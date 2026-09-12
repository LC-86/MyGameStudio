#!/usr/bin/env python3
"""受控远端操作:mgs_remote 经通道的授权交集与失效闭合。

任务票 12 从 tests/test_runtime_gate.py 的原始总入口按真实行为主题拆出;
每条 check 的条件、消息与断言对象与原案例逐字一致(任务票 17 的
「凭据 ∩ 任务授权 ∩ 角色范围 ∩ CONFIG 仓库级授权」受控远端操作),仅重组
位置与准备代码。判定全部经 GateService.remote_record 与 mcp_gate 公开接缝
作出,替身传输层为本地 FakeRemote(零真实远端访问)。原总入口仍聚合本
主题。本主题可直接运行:

    python3 -B tests/test_runtime_gate_remote.py
"""

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from runtime_gate_support import (
    REPO_ROOT, GateService, audit_lines, make_checker, new_instance, run_theme,
)

sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))
import mgs_github  # noqa: E402  (替身传输层错误类型)

FAILURES, check = make_checker()


class FakeRemote:
    """mgs_remote 受控远端操作的本地替身传输层(零网络)。"""

    def __init__(self) -> None:
        self.issues: list[dict] = []
        self.comments: dict[int, list[dict]] = {}
        self.offline = False

    def request(self, method, path, body=None):
        if self.offline:
            raise mgs_github.TransportError("offline", "stand-in offline")
        path = path.split("?", 1)[0]
        base = "/repos/mygamestudio/issue-accept"
        match = re.match(rf"{base}/issues/(\d+)(/.*)?$", path)
        if match:
            number = int(match.group(1))
            if match.group(2) == "/comments" and method == "POST":
                comment = {"id": 7000 + number,
                           "body": body["body"],
                           "created_at": "2026-09-08T12:00:00Z"}
                self.comments[number].append(comment)
                return 201, comment
            if match.group(2) == "/comments" and method == "GET":
                return 200, list(self.comments.get(number, []))
            issue = self.issues[number - 1]
            if method == "GET":
                return 200, issue
            if method == "PATCH":
                for key in ("body", "state", "state_reason"):
                    if key in body:
                        issue[key] = body[key]
                if "labels" in body:
                    issue["labels"] = [{"name": n} for n in body["labels"]]
                return 200, issue
        if method == "GET" and path == base + "/issues":
            return 200, list(self.issues)
        if method == "GET" and path == base + "/labels":
            return 200, [{"name": n} for n in
                         ("triage", "info", "agent-ready", "human-ready",
                          "wont-do")]
        if method == "POST" and path == base + "/issues":
            issue = {"number": len(self.issues) + 1,
                     "id": 1000 + len(self.issues) + 1,
                     "title": body["title"], "body": body["body"],
                     "labels": [{"name": n} for n in body.get("labels", [])],
                     "state": "open", "state_reason": None}
            self.issues.append(issue)
            self.comments[issue["number"]] = []
            return 201, issue
        return 404, {"message": f"no {method} {path}"}


def _remote_fixture(root: Path) -> dict:
    """搭建远端受控操作的最小项目、运行根、替身与两类凭据实例。"""

    project = root / "remote-project"
    docs = project / "docs/mygamestudio"
    docs.mkdir(parents=True)
    (docs / "CONFIG.md").write_text(
        "# 测试项目:协作配置\n\n## 任务来源\n\n"
        "- 后端:github-issues\n"
        "- 当前位置:github.com/mygamestudio/issue-accept\n"
        "- 任务读取规则:GitHub Issues 后端约定\n"
        "- 外部连接引用及已确认操作范围:"
        "github.com/mygamestudio/issue-accept:issues-write(测试授权)\n\n"
        "## 标签映射\n\n| 语义 | 项目标签 |\n| --- | --- |\n"
        "| needs-triage | triage |\n| needs-info | info |\n"
        "| ready-for-agent | agent-ready |\n| ready-for-human | human-ready |\n"
        "| wontfix | wont-do |\n\n"
        "## 文档映射\n\n| 内容 | 当前权威位置 | 维护角色 |\n| --- | --- | --- |\n"
        "| 项目目标与范围 | docs/mygamestudio/PROJECT.md | 制作统筹 |\n"
        "| 游戏需求与设计 | docs/mygamestudio/GAME_DESIGN.md | 方案设计 |\n"
        "| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |\n\n"
        "## 执行条件\n\n- 尚未就绪的能力及影响:无\n", encoding="utf-8")
    for name in ("PROJECT.md", "GAME_DESIGN.md", "TECH_DESIGN.md"):
        (docs / name).write_text(f"# {name}\n\n测试\n", encoding="utf-8")

    runtime_root = root / "remote-runtime"
    svc = GateService(runtime_root)
    svc.init_policy(
        project_root=project,
        roles={
            "producer": ["docs/mygamestudio/PROJECT.md",
                         "github://github.com/mygamestudio/issue-accept/issues/**"],
            "implement": ["src/**", "docs/mygamestudio/work/*/results/**",
                          "github://github.com/mygamestudio/issue-accept/"
                          "issues/*/comments"],
        },
        purposes={"production": None},
    )
    (runtime_root / "remote.json").write_text(json.dumps({
        "github": {"api_base": "http://standin.invalid",
                   "token_env": "MGS_TEST_REMOTE_TOKEN",
                   "cache_dir": str(runtime_root / "gh-cache")},
    }), encoding="utf-8")

    fake = FakeRemote()
    pid, ptok = new_instance(
        svc, "producer",
        ["docs/mygamestudio/PROJECT.md",
         "github://github.com/mygamestudio/issue-accept/issues/**"],
        task="17-remote")
    iid, itok = new_instance(
        svc, "implement",
        ["src/**",
         "github://github.com/mygamestudio/issue-accept/issues/01-alpha/comments"],
        task="01-alpha")
    return {
        "svc": svc, "fake": fake, "ptok": ptok, "itok": itok,
        "runtime_root": runtime_root, "docs": docs,
        "config_path": docs / "CONFIG.md",
        "original_config": (docs / "CONFIG.md").read_text(encoding="utf-8"),
    }


def test_remote_read_create_and_config_authorization(S) -> None:
    """案例 26-28:通道放行、统筹创建留审计、CONFIG 无授权时拒绝。"""

    svc, fake = S["svc"], S["fake"]
    config_path = S["config_path"]
    original_config = S["original_config"]

    # 26. 远端读取经通道放行(凭据 ∩ 任务授权 ∩ 角色范围)
    res = svc.remote_record(S["ptok"], "read", {"identity": "01-alpha"},
                            transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "remote_upstream"
          or res["decision"] == "allow",
          f"读操作应到达上游(任务不存在时报远端侧错误):{res}")

    # 27. 统筹经通道创建远端任务:CONFIG 仓库级授权 + 角色/任务范围都满足
    res = svc.remote_record(S["ptok"], "create",
                            {"identity": "01-alpha", "title": "甲任务",
                             "request": {"当前目标": "演示", "完成标准": "示例",
                                         "执行责任": "Agent(制作实现)"},
                             "triage": "ready-for-agent"}, transport=fake)
    check(res["decision"] == "allow" and res["result"]["created"] is True,
          f"统筹经通道创建远端任务应放行,实际 {res}")
    check(any(e["op"] == "remote:create" and e["decision"] == "allow"
              for e in audit_lines(S["runtime_root"])),
          "远端创建应留下审计记录")

    # 28. 未授权 CONFIG(选择后端不等于授权):改 CONFIG 后同凭据被拒
    config_path.write_text(original_config.replace(
        "github.com/mygamestudio/issue-accept:issues-write(测试授权)",
        "github.com/mygamestudio/issue-accept(仅引用,未授权)"), encoding="utf-8")
    res = svc.remote_record(S["ptok"], "create",
                            {"identity": "02-beta", "title": "乙任务",
                             "request": {}}, transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "remote_scope",
          f"CONFIG 无 issues-write 授权时远端写必须拒绝,实际 {res}")
    check(len(fake.issues) == 1, "被拒时不得产生远端写入")
    config_path.write_text(original_config, encoding="utf-8")


def test_remote_task_grant_and_granularity(S) -> None:
    """案例 29-30:任务授权收窄与路径/角色粒度封顶。"""

    svc, fake = S["svc"], S["fake"]
    itok = S["itok"]

    # 29. 任务授权收窄:实现凭据只能评论自己的任务,改他人正文被拒
    res = svc.remote_record(itok, "append-result",
                            {"identity": "01-alpha",
                             "result_markdown": "已交付。"}, transport=fake)
    check(res["decision"] == "allow",
          f"实现凭据评论本任务结果应放行,实际 {res}")
    res = svc.remote_record(itok, "update",
                            {"identity": "01-alpha", "fields": {"进度": "已完成"}},
                            transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
          f"实现凭据改任务正文应被任务授权拒绝,实际 {res}")
    res = svc.remote_record(itok, "append-result",
                            {"identity": "02-beta", "result_markdown": "越界"},
                            transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
          f"实现凭据评论其他任务应被任务授权拒绝,实际 {res}")

    # 30. 粒度:任务授权只到正文(issues/*)的统筹不能发评论(comments 子路径);
    #     角色只有 comments 的实现即使被宽授权也不能改正文(role_scope 封顶)。
    ptok2 = new_instance(svc, "producer",
                         ["github://github.com/mygamestudio/issue-accept/"
                          "issues/*"], task="17-remote-2")[1]
    res = svc.remote_record(ptok2, "append-result",
                            {"identity": "01-alpha", "result_markdown": "统筹代发"},
                            transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
          f"授权只到 issues/* 的凭不应能发结果评论(comments 子路径),实际 {res}")
    itok2 = new_instance(svc, "implement",
                         ["github://github.com/mygamestudio/issue-accept/"
                          "issues/**"], task="01-alpha-broad")[1]
    res = svc.remote_record(itok2, "update",
                            {"identity": "01-alpha", "fields": {"进度": "已完成"}},
                            transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "role_scope",
          f"实现角色(comments 粒度)即使宽授权也不能改任务正文,实际 {res}")


def test_remote_fail_closed(S) -> None:
    """案例 31-33:上游不可用、凭据/通道失效闭合、非 github 后端拒绝。"""

    svc, fake = S["svc"], S["fake"]
    config_path = S["config_path"]
    original_config = S["original_config"]
    runtime_root = S["runtime_root"]
    ptok = S["ptok"]

    # 31. 上游不可用:失效闭合(不绕行);缓存目录可用时保存未发布草稿
    fake.offline = True
    res = svc.remote_record(ptok, "create",
                            {"identity": "03-gamma", "title": "丙任务",
                             "request": {}}, transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "remote_upstream",
          f"上游不可用应失效闭合拒绝,实际 {res}")
    check((res.get("note") or {}).get("draft")
          and "未发布草稿" in json.dumps(res, ensure_ascii=False),
          f"离线时应保存未发布草稿并回报,实际 {res.get('note')}")
    fake.offline = False

    # 32. 凭据与通道失效闭合:未知令牌 / 缺 remote.json
    res = svc.remote_record("no-such-token", "read", {"identity": "01-alpha"},
                            transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "identity",
          f"未知凭据应拒绝,实际 {res}")
    (runtime_root / "remote.json").rename(runtime_root / "remote.json.bak")
    res = svc.remote_record(ptok, "read", {"identity": "01-alpha"},
                            transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "channel",
          f"远端通道配置缺失应失效闭合,实际 {res}")
    (runtime_root / "remote.json.bak").rename(runtime_root / "remote.json")

    # 33. 项目不是 github 后端 → 拒绝(通道不服务本地后端项目)
    config_path.write_text(original_config.replace(
        "- 后端:github-issues", "- 后端:local-markdown"), encoding="utf-8")
    res = svc.remote_record(ptok, "read", {"identity": "01-alpha"},
                            transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "remote_scope",
          f"本地后端项目走远端通道应拒绝,实际 {res}")
    config_path.write_text(original_config, encoding="utf-8")


def test_remote_record_section() -> None:
    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-remote-"))
    try:
        S = _remote_fixture(root)
        test_remote_read_create_and_config_authorization(S)
        test_remote_task_grant_and_granularity(S)
        test_remote_fail_closed(S)
    finally:
        shutil.rmtree(root, ignore_errors=True)


TESTS = (test_remote_record_section,)

if __name__ == "__main__":
    sys.exit(run_theme("受控远端操作(授权交集与失效闭合)", TESTS, FAILURES))
