#!/usr/bin/env python3
"""运行保障受控写入服务的确定性检查(任务票 02,任务票 11 扩展二进制载荷)。

接缝说明:本脚本覆盖 GateService 的公开接缝——
可信调度侧(init_policy / create_instance / release_instance)与
工作实例侧(scope / write,含任务票 11 的字节载荷 data/content_base64)。
真实 Codex 调用路径(显式入口、沙箱、MCP 通道、模型行为)由
acceptance/02-role-scoped-write/ 覆盖,本脚本不替代。

用法:python3 tests/test_runtime_gate.py
"""

import base64
import hashlib
import json
import re
import shutil
import stat
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "runtime"))

from mgs_runtime import GateService  # noqa: E402
import mcp_gate  # noqa: E402

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def audit_lines(runtime_root: Path) -> list[dict]:
    audit_path = runtime_root / "audit" / "audit.jsonl"
    if not audit_path.is_file():
        return []
    return [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]


def setup_project(root: Path) -> Path:
    project = root / "project"
    (project / "docs/mygamestudio/work/01-status").mkdir(parents=True)
    (project / "src").mkdir(parents=True)
    (project / "docs/mygamestudio/PROJECT.md").write_text("PROJECT-ORIGINAL\n")
    (project / "docs/mygamestudio/GAME_DESIGN.md").write_text("DESIGN-ORIGINAL\n")
    (project / "src/player.js").write_text("// ORIGINAL\n")
    return project


def setup_service(root: Path) -> tuple[GateService, Path]:
    project = setup_project(root)
    runtime_root = root / "runtime"
    svc = GateService(runtime_root)
    svc.init_policy(
        project_root=project,
        roles={
            "producer": ["docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/*/task.md"],
            "design": ["docs/mygamestudio/GAME_DESIGN.md", "prototypes/**"],
            "implement": ["src/**", "assets/**", "docs/mygamestudio/work/*/results/**"],
        },
        purposes={"production": None, "prototype": ["prototypes/**"]},
    )
    return svc, project


def new_instance(svc: GateService, role: str, resources: list[str], purpose: str = "production",
                 ttl: int = 1800, task: str = "T") -> tuple[str, str]:
    inst = svc.create_instance(role=role, task=task, purpose=purpose,
                               resources=resources, ttl_seconds=ttl)
    return inst.instance_id, inst.token


def remote_record_section(root: Path) -> None:
    """任务票 17:mgs_remote 受控远端任务操作(本地替身传输层)。

    语义:远端写入不在会话内直连,而经 mgs-gate 受控通道逐次校验
    「凭据 ∩ 任务授权 ∩ 角色范围 ∩ CONFIG 仓库级授权」;凭据从运行根
    指定的环境变量读取,不进项目记录;上游不可用失效闭合(可存草稿),
    不绕行。
    """

    sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))
    import mgs_github  # noqa: PLC0415
    import mgs_records  # noqa: PLC0415

    class FakeRemote:
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

    # 26. 远端读取经通道放行(凭据 ∩ 任务授权 ∩ 角色范围)
    res = svc.remote_record(ptok, "read", {"identity": "01-alpha"},
                            transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "remote_upstream"
          or res["decision"] == "allow",
          f"读操作应到达上游(任务不存在时报远端侧错误):{res}")

    # 27. 统筹经通道创建远端任务:CONFIG 仓库级授权 + 角色/任务范围都满足
    res = svc.remote_record(ptok, "create",
                            {"identity": "01-alpha", "title": "甲任务",
                             "request": {"当前目标": "演示", "完成标准": "示例",
                                         "执行责任": "Agent(制作实现)"},
                             "triage": "ready-for-agent"}, transport=fake)
    check(res["decision"] == "allow" and res["result"]["created"] is True,
          f"统筹经通道创建远端任务应放行,实际 {res}")
    check(any(e["op"] == "remote:create" and e["decision"] == "allow"
              for e in audit_lines(runtime_root)),
          "远端创建应留下审计记录")

    # 28. 未授权 CONFIG(选择后端不等于授权):改 CONFIG 后同凭据被拒
    config_path = docs / "CONFIG.md"
    original_config = config_path.read_text(encoding="utf-8")
    config_path.write_text(original_config.replace(
        "github.com/mygamestudio/issue-accept:issues-write(测试授权)",
        "github.com/mygamestudio/issue-accept(仅引用,未授权)"), encoding="utf-8")
    res = svc.remote_record(ptok, "create",
                            {"identity": "02-beta", "title": "乙任务",
                             "request": {}}, transport=fake)
    check(res["decision"] == "deny" and res["rule_stage"] == "remote_scope",
          f"CONFIG 无 issues-write 授权时远端写必须拒绝,实际 {res}")
    check(len(fake.issues) == 1, "被拒时不得产生远端写入")
    config_path.write_text(original_config, encoding="utf-8")

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


def review_fix_section(root: Path) -> None:
    """审查修复批(票 02-fix R1–R4)的反例固化,先红后绿。

    反例底稿:.scratch/mygamestudio-v1-review-fixes/evidence/runtime-probes.py
    (2026-09-09 独立审查在 HEAD 6b2444b 复现四项运行保障缺陷):
    - R1 撤销后在途写入仍落盘;
    - R2 用途策略条目丢失时放行(write/scope/远端同类缺省);
    - R3 内容更新破坏已有文件权限位(含回滚路径);
    - R4 审计失败时远端写入已生效却报拒绝。
    """

    # ---------- R1:撤销完成后,在途写入必须拒绝且目标保持原状 ----------
    r1 = root / "r1"
    r1_project = r1 / "project"
    (r1_project / "src").mkdir(parents=True)
    (r1_project / "src/keep.txt").write_text("KEEP\n")
    writer = GateService(r1 / "runtime")
    admin = GateService(r1 / "runtime")
    writer.init_policy(r1_project, {"implement": ["src/**"]},
                       {"production": None})
    r1_inst = writer.create_instance("implement", "T-r1", "production",
                                     ["src/**"])
    original_resolve = writer._resolve_instance
    identity_checked = threading.Event()
    resume = threading.Event()
    outcome: dict = {}

    def pause_after_identity(token):
        resolved = original_resolve(token)
        identity_checked.set()
        assert resume.wait(5)
        return resolved

    writer._resolve_instance = pause_after_identity

    def inflight() -> None:
        outcome["res"] = writer.write(r1_inst.token, "src/inflight.txt",
                                      "STALE\n")

    thread = threading.Thread(target=inflight)
    thread.start()
    check(identity_checked.wait(5), "R1 探针应先停在锁外身份解析")
    revoke = admin.release_instance(r1_inst.instance_id)  # 撤销先于写线程恢复完成
    resume.set()
    thread.join(5)
    check(not thread.is_alive(), "R1 在途写线程应在撤销后返回")
    writer._resolve_instance = original_resolve
    res = outcome.get("res")
    check(revoke["found"], "R1:撤销应成功")
    check(res["decision"] == "deny" and res["rule_stage"] == "identity",
          f"R1:撤销完成后在途写入必须以 identity 拒绝,实际 {res}")
    check(not (r1_project / "src/inflight.txt").exists(),
          "R1:被拒的在途写入不得落盘")
    check((r1_project / "src/keep.txt").read_text() == "KEEP\n",
          "R1:既有目标字节应保持不变")

    # ---------- R2:用途条目缺失 ≠ 显式不额外限制(故障闭合) ----------
    r2 = root / "r2"
    r2_project = r2 / "project"
    (r2_project / "src").mkdir(parents=True)
    r2_svc = GateService(r2 / "runtime")
    r2_svc.init_policy(r2_project, {"implement": ["src/**", "prototypes/**"]},
                       {"production": None, "prototype": ["prototypes/**"]})
    proto = r2_svc.create_instance("implement", "T-r2", "prototype",
                                   ["src/**", "prototypes/**"])
    before = r2_svc.write(proto.token, "src/escaped.txt", "BYPASS\n")
    check(before["decision"] == "deny" and before["rule_stage"] == "purpose",
          f"R2:条目存在时 prototype 用途写 src 应被拒,实际 {before}")
    r2_policy_path = r2 / "runtime" / "policy.json"
    r2_policy = json.loads(r2_policy_path.read_text())
    del r2_policy["purposes"]["prototype"]  # 条目丢失,不是「显式不额外限制」
    r2_policy_path.write_text(json.dumps(r2_policy))
    after = r2_svc.write(proto.token, "src/escaped.txt", "BYPASS\n")
    check(after["decision"] == "deny" and after["rule_stage"] == "purpose",
          f"R2:用途条目缺失时同一写入必须仍被拒(故障闭合),实际 {after}")
    check(not (r2_project / "src/escaped.txt").exists(),
          "R2:被拒写入不得落盘")
    scope_info = r2_svc.scope(proto.token)
    check(scope_info["decision"] == "deny"
          and scope_info["rule_stage"] == "purpose",
          f"R2:scope 对缺失用途条目同样失效闭合,实际 {scope_info}")
    prod = r2_svc.create_instance("implement", "T-r2-prod", "production",
                                  ["src/**"])
    ok_write = r2_svc.write(prod.token, "src/ok.txt", "OK\n")
    check(ok_write["decision"] == "allow",
          f"R2:显式空条目(restrict=None)保持「不额外限制」语义,实际 {ok_write}")
    r2_policy["purposes"]["prototype"] = {"oops": True}  # 条目形状无效
    r2_policy_path.write_text(json.dumps(r2_policy))
    broken = r2_svc.write(prod.token, "src/ok2.txt", "X\n")
    check(broken["decision"] == "deny" and broken["rule_stage"] == "policy",
          f"R2:用途条目结构无效应按策略不完整拒绝,实际 {broken}")
    check(not (r2_project / "src/ok2.txt").exists(),
          "R2:策略无效时不得落盘")

    # ---------- R3:内容更新(含回滚)保留既有目标的权限位 ----------
    r3 = root / "r3"
    r3_project = r3 / "project"
    (r3_project / "src").mkdir(parents=True)
    r3_svc = GateService(r3 / "runtime")
    r3_svc.init_policy(r3_project, {"implement": ["src/**"]},
                       {"production": None})
    r3_inst = r3_svc.create_instance("implement", "T-r3", "production",
                                     ["src/**"])
    for name, mode_bits in (("run.sh", 0o755), ("private.txt", 0o600),
                            ("normal.txt", 0o644)):
        target = r3_project / "src" / name
        target.write_text("old\n")
        target.chmod(mode_bits)
        res = r3_svc.write(r3_inst.token, f"src/{name}", "new\n",
                           expected_sha256=hashlib.sha256(b"old\n").hexdigest())
        actual = stat.S_IMODE(target.stat().st_mode)
        check(res["decision"] == "allow",
              f"R3:{name} 合法内容更新应放行,实际 {res}")
        check(actual == mode_bits,
              f"R3:{name} 内容更新后权限位应保持 {oct(mode_bits)},"
              f"实际 {oct(actual)}")
    res = r3_svc.write(r3_inst.token, "src/fresh.txt", "fresh\n")
    # 新建文件按默认 0644 创建;umask 只做减法,断言属主读写位必然在
    # (umask 敏感性:不在本票范围,既有新建语义保持不变)
    fresh_mode = stat.S_IMODE((r3_project / "src/fresh.txt").stat().st_mode)
    check(res["decision"] == "allow" and fresh_mode & 0o600 == 0o600,
          f"R3:新建文件应正常落盘(实际权限 {oct(fresh_mode)}),实际 {res}")
    r3_audit = r3 / "runtime" / "audit" / "audit.jsonl"
    r3_audit.unlink()
    r3_audit.mkdir()  # 审计不可用 → 落盘后回滚
    script = r3_project / "src/run.sh"
    res = r3_svc.write(r3_inst.token, "src/run.sh", "ROLLED\n")
    check(res["decision"] == "deny" and res["rule_stage"] == "audit",
          f"R3:审计不可用应回滚并拒绝,实际 {res}")
    check(script.read_text() == "new\n"
          and stat.S_IMODE(script.stat().st_mode) == 0o755,
          "R3:回滚后内容与权限位都应恢复原状(0755 不得被降级)")
    r3_audit.rmdir()

    # ---------- R4:远端写入先记审计意图;结果审计失败时如实回报 ----------
    sys.path.insert(0, str(REPO_ROOT / "tests"))
    import test_github_backend as gh_fixtures  # noqa: PLC0415
    sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))

    r4 = root / "r4"
    r4_project = gh_fixtures.make_github_project(r4 / "project")
    r4_svc = GateService(r4 / "runtime")
    r4_resources = ["github://github.com/mygamestudio/issue-accept/issues/**"]
    r4_svc.init_policy(r4_project, {"producer": r4_resources},
                       {"production": None})
    r4_inst = r4_svc.create_instance("producer", "T-r4", "production",
                                     r4_resources)
    r4_svc._write_json("remote.json", {"github": {
        "api_base": "http://unused.invalid", "token_env": "MGS_TEST_UNUSED",
        "cache_dir": str(r4 / "cache")}})
    transport = gh_fixtures.FakeTransport()
    transport.seed_issue("01-task", "Existing")
    r4_audit = r4 / "runtime" / "audit" / "audit.jsonl"

    class Facade:
        def remote_record(self, token, action, payload):
            return r4_svc.remote_record(token, action, payload,
                                        transport=transport)

    def mgs_remote(action: str, payload: dict) -> dict:
        response = mcp_gate.handle_tools_call(
            Facade(), "mgs_remote",
            {"token": r4_inst.token, "action": action, "payload": payload})
        return json.loads(response["content"][0]["text"])

    # R4a:审计不可用时,远端动作不得执行;MCP 入口如实拒绝,
    #     不出现「远端已新增评论却报告拒绝且无审计」。
    r4_audit.unlink()
    r4_audit.mkdir()
    body = mgs_remote("append-result", {"identity": "01-task",
                                        "result_markdown": "审计不可用"})
    check(body["decision"] == "deny" and body["rule_stage"] == "audit",
          f"R4:审计不可用时远端写入应在执行前拒绝(意图无法持久记录),实际 {body}")
    check(len(transport.comments[1]) == 0,
          "R4:审计不可用时不得执行远端动作(替身零新增评论)")
    check(not r4_audit.is_file(), "R4:审计路径不可写时不得伪造审计文件")
    r4_audit.rmdir()

    # R4b:意图已持久记录、结果审计追加失败:远端结果如实回报,
    #     不包装成拒绝,不静默丢弃记录责任。
    real_audit_unlocked = r4_svc._audit_unlocked
    audit_calls = {"n": 0}

    def flaky_audit_unlocked(entry):
        audit_calls["n"] += 1
        if audit_calls["n"] >= 2:  # 第 1 次(意图)落盘,第 2 次(结果)失败
            raise OSError("injected outcome-audit failure")
        return real_audit_unlocked(entry)

    r4_svc._audit_unlocked = flaky_audit_unlocked
    try:
        res = r4_svc.remote_record(
            r4_inst.token, "append-result",
            {"identity": "01-task", "result_markdown": "结果审计失败"},
            transport=transport)
    finally:
        r4_svc._audit_unlocked = real_audit_unlocked
    check(res["decision"] == "allow" and res.get("audit_recorded") is False,
          f"R4:远端动作已生效时不得包装成拒绝,应如实回报并标注审计未记录,"
          f"实际 {res}")
    check("granted by" in res.get("reason", ""),
          f"R4:结果审计失败的回报应保留策略依据 reason,实际 {res.get('reason')}")
    check(len(transport.comments[1]) == 1,
          "R4:结果审计失败不应否认已发生的远端写入")
    r4_entries = audit_lines(r4 / "runtime")
    check(any(e.get("op") == "remote:append-result"
              and e.get("decision") == "intent" for e in r4_entries),
          "R4:远端写入意图应先于执行持久记录")
    check(not any(e.get("op") == "remote:append-result"
                  and e.get("decision") == "allow" for e in r4_entries),
          "R4:结果审计失败时不得伪造已记录的结果条目")

    # R2-remote:用途条目缺失对远端路径同样失效闭合(同类缺省逻辑)。
    r4_policy_path = r4 / "runtime" / "policy.json"
    r4_policy = json.loads(r4_policy_path.read_text())
    del r4_policy["purposes"]["production"]
    r4_policy_path.write_text(json.dumps(r4_policy))
    res = r4_svc.remote_record(
        r4_inst.token, "append-result",
        {"identity": "01-task", "result_markdown": "条目缺失"},
        transport=transport)
    check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
          f"R2:用途条目缺失时远端操作必须拒绝,实际 {res}")
    check(len(transport.comments[1]) == 1, "R2:远端拒绝时不得产生新评论")
    r4_policy["purposes"]["production"] = {"restrict": None}
    r4_policy_path.write_text(json.dumps(r4_policy))
    res = r4_svc.remote_record(
        r4_inst.token, "append-result",
        {"identity": "01-task", "result_markdown": "条目恢复"},
        transport=transport)
    check(res["decision"] == "allow"
          and res.get("audit_recorded") is None
          and len(transport.comments[1]) == 2,
          f"R2:恢复显式空条目后远端写入应回到放行,实际 {res}")

    # R1-remote:撤销完成后,在途远端写入同样拒绝(远端零调用)。
    # 与本地 R1 同一时序:写线程停在锁外身份解析后,撤销先完成再恢复。
    r1r_inst = r4_svc.create_instance("producer", "T-r1r", "production",
                                      r4_resources)
    calls_before = len(transport.calls)
    original_resolve_r = r4_svc._resolve_instance
    r1r_checked = threading.Event()
    r1r_resume = threading.Event()
    r1r_outcome: dict = {}

    def r1r_pause(token):
        resolved = original_resolve_r(token)
        if token == r1r_inst.token:
            r1r_checked.set()
            assert r1r_resume.wait(5)
        return resolved

    def r1r_inflight() -> None:
        r1r_outcome["res"] = r4_svc.remote_record(
            r1r_inst.token, "append-result",
            {"identity": "01-task", "result_markdown": "撤销后在途"},
            transport=transport)

    r4_svc._resolve_instance = r1r_pause
    thread = threading.Thread(target=r1r_inflight)
    thread.start()
    try:
        check(r1r_checked.wait(5), "R1-remote:探针应先停在锁外身份解析")
        revoke_r = r4_svc.release_instance(r1r_inst.instance_id)
        r1r_resume.set()
        thread.join(5)
        check(not thread.is_alive(), "R1-remote:在途远端线程应在撤销后返回")
    finally:
        r4_svc._resolve_instance = original_resolve_r
        r1r_resume.set()
    res = r1r_outcome.get("res")
    check(revoke_r["found"], "R1-remote:撤销应成功")
    check(res is not None and res["decision"] == "deny"
          and res["rule_stage"] == "identity",
          f"R1-remote:撤销完成后在途远端写入必须拒绝,实际 {res}")
    check(len(transport.calls) == calls_before,
          "R1-remote:被拒的远端写入不得发出任何远端调用")


def records_review_fix_section(root: Path) -> None:
    """审查修复批(票 01-fix)在运行时通道侧的反例固化,先红后绿。

    - 核验建议 2(在线执行路径):安排更新说明经通道传递到远端正文,
      不回退默认文案;
    - S2(通道级):评论超时且回读失败 → 结果不确定;通道如实回报,
      不包装成「已保存草稿」的拒绝,也不发第二条创建请求。
    """

    sys.path.insert(0, str(REPO_ROOT / "tests"))
    import test_github_backend as gh_fixtures  # noqa: PLC0415

    base = root / "t01"
    project = gh_fixtures.make_github_project(base / "project")
    svc = GateService(base / "runtime")
    resources = ["github://github.com/mygamestudio/issue-accept/issues/**"]
    svc.init_policy(project, {"producer": resources}, {"production": None})
    inst = svc.create_instance("producer", "T-01x", "production", resources)
    svc._write_json("remote.json", {"github": {
        "api_base": "http://unused.invalid", "token_env": "MGS_TEST_UNUSED",
        "cache_dir": str(base / "cache")}})
    fake = gh_fixtures.FakeTransport()
    fake.seed_issue("01-task", "Existing")

    # 核验建议 2(在线执行路径):说明随通道动作参数传递
    res = svc.remote_record(inst.token, "update",
                            {"identity": "01-task",
                             "fields": {"进度": "执行中"},
                             "change_note": "通道轮安排"},
                            transport=fake)
    check(res["decision"] == "allow", f"通道内安排更新应放行,实际 {res}")
    check("通道轮安排" in fake.issues[0]["body"],
          "通道在线路径的更新说明应写入远端正文状态变化(不回退默认文案)")

    # S2(通道级):回读失败 → 结果不确定,如实回报
    fake.drop("POST", "/comments")
    fake.fail("GET", "/comments", "timeout")
    comments_before = len(fake.comments[1])
    res = svc.remote_record(inst.token, "append-result",
                            {"identity": "01-task",
                             "result_markdown": "回读失败"},
                            transport=fake)
    posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
    check(len(posts) == comments_before + 1,
          f"回读失败后不得重发评论,实际共 {len(posts)} 次 POST(此前 "
          f"{comments_before} 次)")
    check(res.get("decision") == "uncertain"
          and res.get("result", {}).get("uncertain") is True,
          f"通道应如实回报结果不确定(不虚报成功也不包装成拒绝),实际 {res}")
    check("草稿" not in json.dumps(res.get("note") or {}, ensure_ascii=False),
          "不确定结果不得被包装成「已保存草稿」的拒绝")


def review2_sp1_section(root: Path) -> None:
    """第二轮审查修复批(票 review2-01):SP-1 反例固化,先红后绿。

    反例底稿:.scratch/mygamestudio-v1-review2-fixes/evidence/extra_probes.py
    的 remote-config-revoke-inflight 块(2026-09-09 独立复审在 HEAD b89b548
    复现):remote_record 在锁外读取 CONFIG 仓库授权并构建 backend,锁内只
    重读身份与 policy——把在途请求暂停在取锁前,另一 GateService 经正常
    write 入口(内容哈希正确)撤销 CONFIG 的 issues-write 后恢复原请求,
    仍 allow 且替身新增评论。期望:最终临界区内重读 CONFIG 授权与目标并
    据此构建 backend,在途请求 deny/remote_scope、远端零写入(records
    合同:创建或修改远端记录前核对明确的仓库及操作授权)。
    """

    sys.path.insert(0, str(REPO_ROOT / "tests"))
    import test_github_backend as gh_fixtures  # noqa: PLC0415

    base = root / "review2-sp1"
    project = gh_fixtures.make_github_project(base / "project")
    runtime = base / "runtime"
    svc = GateService(runtime)
    peer = GateService(runtime)  # 另一会话入口,与探针的双 GateService 时序一致
    resources = ["github://github.com/mygamestudio/issue-accept/issues/**",
                 "docs/mygamestudio/CONFIG.md"]
    svc.init_policy(project, {"producer": resources}, {"production": None})
    inst = svc.create_instance("producer", "remote", "production", resources)
    admin = svc.create_instance("producer", "config-update", "production",
                                resources)
    svc._write_json("remote.json", {"github": {
        "api_base": "http://unused.invalid", "token_env": "MGS_TEST_UNUSED",
        "cache_dir": str(base / "cache")}})
    transport = gh_fixtures.FakeTransport()
    transport.seed_issue("01-task", "Existing")

    # 基线:撤销前合法远端写入放行(授权在场,语义与性能不回退的前提)
    ok = peer.remote_record(inst.token, "append-result",
                            {"identity": "01-task", "result_markdown": "撤销前"},
                            transport=transport)
    check(ok["decision"] == "allow",
          f"SP-1:撤销前合法远端写入应放行,实际 {ok}")
    check(len(transport.comments[1]) == 1,
          f"SP-1:撤销前应恰新增 1 条评论,实际 {len(transport.comments[1])}")

    # 在途时序:写线程停在取锁前(锁外 CONFIG 已读完),撤销先完成再恢复。
    # 与 R1-remote 的差别:暂停点在锁本身,覆盖「锁外 CONFIG 读取→取锁」窗口。
    real_lock = svc._locked
    waiting = threading.Event()
    resume = threading.Event()
    outcome: dict = {}

    def paused_lock():
        if threading.current_thread().name == "remote-writer":
            waiting.set()
            assert resume.wait(5)
        return real_lock()

    def inflight() -> None:
        try:
            outcome["res"] = svc.remote_record(
                inst.token, "append-result",
                {"identity": "01-task", "result_markdown": "撤销后在途"},
                transport=transport)
        except Exception as exc:  # noqa: BLE001 - 异常本身即断言素材
            outcome["error"] = repr(exc)

    svc._locked = paused_lock
    thread = threading.Thread(target=inflight, name="remote-writer")
    thread.start()
    try:
        check(waiting.wait(5), "SP-1:在途请求应先暂停在取锁前")
        config = project / "docs/mygamestudio/CONFIG.md"
        old_text = config.read_text(encoding="utf-8")
        new_text = old_text.replace(gh_fixtures.AUTH, "无(已撤销)")
        check(new_text != old_text, "SP-1:探针应实际改写 CONFIG 授权行")
        rev = peer.write(admin.token, "docs/mygamestudio/CONFIG.md", new_text,
                         expected_sha256=hashlib.sha256(
                             old_text.encode()).hexdigest())
        check(rev["decision"] == "allow",
              f"SP-1:经正常入口撤销 CONFIG 授权应 allow,实际 {rev}")
        resume.set()
        thread.join(5)
        check(not thread.is_alive(), "SP-1:在途线程应在撤销后返回")
    finally:
        svc._locked = real_lock
        resume.set()
    res = outcome.get("res")
    check(outcome.get("error") is None,
          f"SP-1:在途请求不应异常,实际 {outcome.get('error')}")
    check(res is not None and res["decision"] == "deny"
          and res["rule_stage"] == "remote_scope",
          f"SP-1:CONFIG 授权撤销后,在途远端写入必须以 remote_scope 拒绝,"
          f"实际 {res}")
    check(len(transport.comments[1]) == 1,
          f"SP-1:被拒的在途请求不得产生远端写入(评论数应保持 1,"
          f"实际 {len(transport.comments[1])})")
    posts = [c for c in transport.calls
             if c[0] == "POST" and "/comments" in c[1]]
    check(len(posts) == 1,
          f"SP-1:全程应只发出撤销前那 1 次评论 POST,实际 {len(posts)} 次")

    # 撤销后新请求继续拒绝(既有语义不回退);拒绝如实进审计
    fresh = peer.remote_record(inst.token, "append-result",
                               {"identity": "01-task",
                                "result_markdown": "撤销后新请求"},
                               transport=transport)
    check(fresh["decision"] == "deny" and fresh["rule_stage"] == "remote_scope",
          f"SP-1:撤销后新远端请求应继续拒绝,实际 {fresh}")
    entries = audit_lines(runtime)
    check(any(e.get("op") == "remote:append-result"
              and e.get("decision") == "deny"
              and e.get("rule_stage") == "remote_scope" for e in entries),
          "SP-1:在途拒绝应留下 remote_scope 审计记录")


def review2_sp2_section(root: Path) -> None:
    """第二轮审查修复批(票 review2-02):SP-2 通道级反例固化,先红后绿。

    反例底稿:.scratch/mygamestudio-v1-review2-fixes/evidence/partial_remote_probe.py
    (2026-09-09 独立复审在 HEAD b89b548 复现):注入「评论 POST 成功+索引
    PATCH 超时」,mgs_github.append_result 在评论创建后直接抛出、
    mgs_runtime.remote_record 把它整体转成 deny/remote_upstream(不携带
    comment_id);故障清除后同请求重试返回 allow,替身累计 2 条重复评论。
    期望:部分成功如实保留(结果携带已发布评论身份与未完成状态,非整体
    deny);恢复后重试只补索引,替身评论数恰 1(runtime 合同第 16 行:
    已写入待表达)。
    """

    sys.path.insert(0, str(REPO_ROOT / "tests"))
    import test_github_backend as gh_fixtures  # noqa: PLC0415

    base = root / "review2-sp2"
    project = gh_fixtures.make_github_project(base / "project")
    svc = GateService(base / "runtime")
    resources = ["github://github.com/mygamestudio/issue-accept/issues/**"]
    svc.init_policy(project, {"producer": resources}, {"production": None})
    inst = svc.create_instance("producer", "T-sp2", "production", resources)
    svc._write_json("remote.json", {"github": {
        "api_base": "http://unused.invalid", "token_env": "MGS_TEST_UNUSED",
        "cache_dir": str(base / "cache")}})
    fake = gh_fixtures.FakeTransport()
    fake.seed_issue("01-task", "Existing")
    fake.fail("PATCH", "/issues/1", "timeout")  # 评论 POST 成功后索引 PATCH 超时

    class Facade:
        def remote_record(self, token, action, payload):
            return svc.remote_record(token, action, payload, transport=fake)

    def call() -> dict:
        response = mcp_gate.handle_tools_call(
            Facade(), "mgs_remote",
            {"token": inst.token, "action": "append-result",
             "payload": {"identity": "01-task", "result_markdown": "same result"}})
        return json.loads(response["content"][0]["text"])

    first = call()
    check(first.get("decision") != "deny",
          f"SP-2:评论已发布的部分成功不得整体转 deny,实际 {first}")
    first_result = first.get("result") or {}
    check(first_result.get("published") is True
          and first_result.get("comment_id") is not None,
          f"SP-2:结果应携带已发布评论身份,实际 {first_result}")
    check(first_result.get("index_updated") is False,
          f"SP-2:未完成部分(结果索引)应如实表达,实际 {first_result}")
    check(len(fake.comments[1]) == 1,
          f"SP-2:首次调用替身应已有 1 条评论,实际 {len(fake.comments[1])} 条")

    # 故障清除后同请求重试:仅补索引,不重复发布评论
    fake._fail = []
    second = call()
    check(second.get("decision") == "allow",
          f"SP-2:恢复后重试应 allow,实际 {second}")
    check(len(fake.comments[1]) == 1,
          f"SP-2:恢复后重试仅补索引,替身评论数应恰 1(不重复发布),"
          f"实际 {len(fake.comments[1])} 条")
    posts = [c for c in fake.calls if c[0] == "POST" and "/comments" in c[1]]
    check(len(posts) == 1,
          f"SP-2:全程应只发出 1 次评论 POST,实际 {len(posts)} 次")
    check(f"#issuecomment-{first_result.get('comment_id')}"
          in (fake.issues[0].get("body") or ""),
          "SP-2:重试后结果索引应补齐该评论引用")
    entries = audit_lines(base / "runtime")
    check(any(e.get("op") == "remote:append-result"
              and e.get("decision") == "intent" for e in entries),
          "SP-2:远端写入意图仍先于执行持久记录")


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-test-"))
    try:
        svc, project = setup_service(root)
        design = project / "docs/mygamestudio/GAME_DESIGN.md"
        code = project / "src/player.js"
        mgmt = project / "docs/mygamestudio/PROJECT.md"

        # 1. 统筹管理写入成功
        pid, ptok = new_instance(svc, "producer",
                                 ["docs/mygamestudio/PROJECT.md",
                                  "docs/mygamestudio/work/01-status/task.md"])
        res = svc.write(ptok, "docs/mygamestudio/PROJECT.md", "PROJECT-UPDATED\n",
                        note="统筹更新管理记录")
        check(res["decision"] == "allow", f"统筹管理写入应成功,实际 {res}")
        check(mgmt.read_text() == "PROJECT-UPDATED\n", "管理文件应写入新内容")

        # 2. 统筹对产品设计与正式代码的写入被拒,目标字节不变
        #    (实际令牌的任务授权只含管理路径,先落在任务授权层)
        for target, label in (("docs/mygamestudio/GAME_DESIGN.md", "产品设计"),
                              ("src/player.js", "正式代码")):
            before = (project / target).read_bytes()
            res = svc.write(ptok, target, "OVERWRITE\n", note="越界尝试")
            check(res["decision"] == "deny", f"统筹写{label}应被拒绝,实际 {res}")
            check(res["rule_stage"] in ("role_scope", "task_grant"),
                  f"统筹写{label}拒绝依据应为角色范围或任务授权,实际 {res.get('rule_stage')}")
            check((project / target).read_bytes() == before,
                  f"被拒后{label}字节应保持不变")

        # 2b. 即使任务授权被放宽,角色范围仍然封顶统筹的可写集合
        bid2, btok2 = new_instance(svc, "producer",
                                   ["docs/mygamestudio/PROJECT.md", "src/**",
                                    "docs/mygamestudio/GAME_DESIGN.md"],
                                   task="T-broad")
        for target, label in (("docs/mygamestudio/GAME_DESIGN.md", "产品设计"),
                              ("src/player.js", "正式代码")):
            before = (project / target).read_bytes()
            res = svc.write(btok2, target, "OVERWRITE\n")
            check(res["decision"] == "deny" and res["rule_stage"] == "role_scope",
                  f"宽授权统筹写{label}仍应被角色范围拒绝,实际 {res}")
            check((project / target).read_bytes() == before,
                  f"宽授权被拒后{label}字节应保持不变")
        svc.release_instance(bid2)

        # 3. 制作实现的合法写入(代码 + 结果记录)
        iid, itok = new_instance(svc, "implement",
                                 ["src/player.js",
                                  "docs/mygamestudio/work/01-status/results/**"],
                                 task="T-code")
        res = svc.write(itok, "src/player.js", "// UPDATED BY IMPLEMENT\n")
        check(res["decision"] == "allow", f"实现角色写代码应成功,实际 {res}")
        check(code.read_text() == "// UPDATED BY IMPLEMENT\n", "代码文件应写入新内容")
        res = svc.write(itok, "docs/mygamestudio/work/01-status/results/2026-09-08.md",
                        "# 结果\n")
        check(res["decision"] == "allow", f"实现角色写结果记录应成功,实际 {res}")
        check((project / "docs/mygamestudio/work/01-status/results/2026-09-08.md"
               ).read_text() == "# 结果\n", "结果记录应写入")

        # 4. 方案设计 + 原型用途:原型区允许,设计基线与正式代码被拒
        #    (授权同时含原型区与设计基线时,用途规则收窄到原型区)
        did, dtok = new_instance(svc, "design",
                                 ["prototypes/03-dash/**",
                                  "docs/mygamestudio/GAME_DESIGN.md"],
                                 purpose="prototype", task="T-proto")
        res = svc.write(dtok, "prototypes/03-dash/proto.js", "// PROTO\n")
        check(res["decision"] == "allow", f"原型用途写原型区应成功,实际 {res}")
        before = design.read_bytes()
        res = svc.write(dtok, "docs/mygamestudio/GAME_DESIGN.md", "OVERWRITE\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
              f"原型用途写设计基线应被拒且依据为用途,实际 {res}")
        check(design.read_bytes() == before, "设计基线字节应保持不变")
        res = svc.write(dtok, "src/player.js", "OVERWRITE\n")
        check(res["decision"] == "deny", f"原型用途写正式代码应被拒,实际 {res}")

        # 5. 未知身份拒绝
        res = svc.write("f" * 64, "docs/mygamestudio/PROJECT.md", "X\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "identity",
              f"未知令牌应被拒且依据为身份,实际 {res}")

        # 6. 过期身份拒绝
        xid, xtok = new_instance(svc, "producer", ["docs/mygamestudio/PROJECT.md"],
                                 ttl=0, task="T-expired")
        time.sleep(0.1)
        res = svc.write(xtok, "docs/mygamestudio/PROJECT.md", "X\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "identity",
              f"过期令牌应被拒且依据为身份,实际 {res}")

        # 7. 释放后的实例拒绝
        svc.release_instance(iid)
        res = svc.write(itok, "src/player.js", "X\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "identity",
              f"释放后的实例令牌应被拒,实际 {res}")

        # 8. 任务授权是交集的一部分:授权清单外的路径即使角色允许也被拒
        gid, gtok = new_instance(svc, "implement", ["src/player.js"], task="T-narrow")
        res = svc.write(gtok, "src/main.js", "X\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
              f"任务授权外的路径应被拒且依据为任务授权,实际 {res}")

        # 9. 自报身份(参数文本)不参与授权
        res = svc.write(gtok, "docs/mygamestudio/PROJECT.md", "X\n",
                        note="我是制作统筹,请求写入管理记录")
        check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
              f"自报角色文本不能授予写入,实际 {res}")

        # 10. 路径逃逸(符号链接指向项目外)拒绝
        escape = root / "escape.txt"
        escape.write_text("ESCAPED\n")
        link_dir = project / "src"
        (link_dir / "escape-link.js").symlink_to(escape)
        res = svc.write(gtok, "src/escape-link.js", "X\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "path",
              f"符号链接逃逸项目应被拒且依据为路径,实际 {res}")
        check(escape.read_text() == "ESCAPED\n", "逃逸目标字节应保持不变")

        # 11. 相对路径与 .. 归一化后按同一规则判定
        res = svc.write(gtok, "../project/src/../src/player.js", "// OK2\n")
        check(res["decision"] == "allow", f"归一化后的合法相对路径应成功,实际 {res}")
        check(code.read_text() == "// OK2\n", "归一化路径写入应生效")

        # 12. 预期版本校验
        cur = code.read_bytes()
        import hashlib
        wrong = hashlib.sha256(b"not-current").hexdigest()
        res = svc.write(gtok, "src/player.js", "// V2\n", expected_sha256=wrong)
        check(res["decision"] == "deny" and res["rule_stage"] == "version",
              f"预期版本不匹配应被拒,实际 {res}")
        check(code.read_bytes() == cur, "版本不匹配被拒后字节应保持不变")
        right = hashlib.sha256(cur).hexdigest()
        res = svc.write(gtok, "src/player.js", "// V3\n", expected_sha256=right)
        check(res["decision"] == "allow", f"预期版本匹配应成功,实际 {res}")
        check(code.read_text() == "// V3\n", "版本匹配写入应生效")

        # 13. 单写入者占用(先结束仍持有占用的早期实例)
        svc.release_instance(gid)
        aid, atok = new_instance(svc, "implement", ["src/player.js"], task="T-a")
        bid, btok = new_instance(svc, "implement", ["src/player.js"], task="T-b")
        res = svc.write(atok, "src/player.js", "// A\n")
        check(res["decision"] == "allow", f"实例 A 首写应成功,实际 {res}")
        res = svc.write(btok, "src/player.js", "// B\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"实例 B 在 A 占用期间写入应被拒,实际 {res}")
        res = svc.write(atok, "src/player.js", "// A2\n")
        check(res["decision"] == "allow", f"同一实例重复写入应成功,实际 {res}")
        svc.release_instance(aid)
        res = svc.write(btok, "src/player.js", "// B2\n")
        check(res["decision"] == "allow", f"释放占用后实例 B 写入应成功,实际 {res}")

        # 14. 工作实例操作不能改变策略
        policy_path = root / "runtime" / "policy.json"
        policy_before = policy_path.read_bytes()
        for tok in (atok, btok, ptok, dtok):
            svc.scope(tok)
        check(policy_path.read_bytes() == policy_before,
              "工作实例的 scope/write 操作不得修改策略文件")

        # 15. scope 返回有效交集与身份,不泄露令牌
        info = svc.scope(ptok)
        check(info["decision"] == "allow", f"统筹 scope 应成功,实际 {info}")
        check(info["role"] == "producer" and info["task"] == "T", "scope 应返回绑定身份")
        check(info["purpose"] == "production", "scope 应返回用途")
        check(any("PROJECT.md" in p for p in info["allowed"]),
              f"scope 应列出统筹可写资源,实际 {info['allowed']}")
        check(all(p not in json.dumps(info) for p in ("token", ptok)),
              "scope 输出不得包含原始令牌")

        # 16. 审计记录字段完整(允许与拒绝)
        entries = audit_lines(root / "runtime")
        allows = [e for e in entries if e.get("decision") == "allow"]
        denies = [e for e in entries if e.get("decision") == "deny"]
        check(len(allows) >= 8, f"应记录至少 8 条允许,实际 {len(allows)}")
        check(len(denies) >= 10, f"应记录至少 10 条拒绝,实际 {len(denies)}")
        required = ("ts", "op", "decision", "reason", "rule_stage",
                    "instance_id", "task", "role", "purpose", "target",
                    "policy_sha256", "basis")
        for entry in entries:
            missing = [f for f in required if f not in entry]
            check(not missing, f"审计记录缺字段 {missing}:{entry}")
        identity_denials = [e for e in denies if e["rule_stage"] == "identity"]
        check(all(e.get("token_fp") and not e.get("token_raw")
                  for e in identity_denials),
              "身份拒绝应记录令牌指纹而非原始令牌")

        # 17. 登记文件不保存原始令牌
        registry = (root / "runtime" / "instances.json").read_text()
        for tok in (ptok, itok, dtok, gtok, atok, btok):
            check(tok not in registry, "登记文件不得包含原始令牌")

        # 18. 委派后统筹可写范围不扩大
        res = svc.write(ptok, "src/player.js", "X\n")
        check(res["decision"] == "deny" and res["rule_stage"] in ("role_scope", "task_grant"),
              f"委派专业工作后统筹写代码仍应被拒,实际 {res}")

        # 19. 二进制资源写入(任务票 11):音频等非文本资源以字节载荷经受控通道。
        #     语义与文本写入一致:同一授权交集、同一字节级版本校验与审计。
        import hashlib
        wav = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00" + bytes(range(256))
        xid, xtok = new_instance(svc, "implement",
                                 ["assets/audio/**",
                                  "docs/mygamestudio/work/01-status/results/**"],
                                 task="T-audio")
        res = svc.write(xtok, "assets/audio/warning.wav", data=wav,
                        note="预警音二进制写入")
        check(res["decision"] == "allow", f"二进制资源写入应成功,实际 {res}")
        audio_path = project / "assets/audio/warning.wav"
        check(audio_path.read_bytes() == wav, "二进制文件字节应逐字节一致(非 UTF-8 也能落盘)")
        check(res["bytes"] == len(wav)
              and res["written_sha256"] == hashlib.sha256(wav).hexdigest(),
              f"审计口径应按字节记录大小与哈希,实际 {res.get('bytes'), res.get('written_sha256')}")
        # 基于字节的版本校验对二进制同样生效
        res = svc.write(xtok, "assets/audio/warning.wav", data=wav + b"\x00",
                        expected_sha256=hashlib.sha256(wav).hexdigest())
        check(res["decision"] == "allow", f"字节级版本匹配的二进制更新应成功,实际 {res}")
        check(audio_path.read_bytes() == wav + b"\x00", "二进制更新应写入新字节")
        # 越界二进制同样被拒,目标字节不变
        before = code.read_bytes()
        res = svc.write(xtok, "src/player.js", data=b"\x89PNG\r\n\x1a\n")
        check(res["decision"] == "deny" and res["rule_stage"] in ("role_scope", "task_grant"),
              f"任务授权外的二进制写入应被拒,实际 {res}")
        check(code.read_bytes() == before, "被拒后目标字节应保持不变")
        svc.release_instance(xid)

        # 20. mgs-gate 通道参数校验(任务票 11):content 与 content_base64 恰一,
        #     非法 base64 与缺失载荷都按通道参数错误失效闭合,不落盘。
        def gate_call(args: dict) -> dict:
            payload = mcp_gate.handle_tools_call(svc, "mgs_write", args)
            return json.loads(payload["content"][0]["text"])

        yid, ytok = new_instance(svc, "implement", ["assets/audio/**"], task="T-b64")
        res = gate_call({"token": ytok, "path": "assets/audio/x.wav",
                         "content": "x", "content_base64": base64.b64encode(b"x").decode()})
        check(res["decision"] == "deny" and res["rule_stage"] == "channel",
              f"content 与 content_base64 同时提供应按通道参数错误拒绝,实际 {res}")
        res = gate_call({"token": ytok, "path": "assets/audio/x.wav"})
        check(res["decision"] == "deny" and res["rule_stage"] == "channel",
              f"载荷完全缺失应按通道参数错误拒绝,实际 {res}")
        check(not (project / "assets/audio/x.wav").exists(),
              "参数错误的调用不得落盘")
        res = gate_call({"token": ytok, "path": "assets/audio/x.wav",
                         "content_base64": "!!not-base64!!"})
        check(res["decision"] == "deny" and res["rule_stage"] == "channel",
              f"非法 base64 应按通道参数错误拒绝,实际 {res}")
        # 命令行 base64 工具的换行折行被容忍(剥掉空白后严格解码)
        wrapped = base64.encodebytes(wav)  # 每 76 字符折行,含换行
        check(b"\n" in wrapped, "encodebytes 应产生带换行的折行输出")
        res = gate_call({"token": ytok, "path": "assets/audio/wrapped.wav",
                         "content_base64": wrapped.decode()})
        check(res["decision"] == "allow", f"带换行折行的 base64 载荷应被接受,实际 {res}")
        check((project / "assets/audio/wrapped.wav").read_bytes() == wav,
              "折行 base64 写入的字节应与原字节一致")
        res = gate_call({"token": ytok, "path": "assets/audio/ok.wav",
                         "content_base64": base64.b64encode(wav).decode(),
                         "note": "通道侧 base64 载荷"})
        check(res["decision"] == "allow", f"通道侧 base64 载荷写入应成功,实际 {res}")
        check((project / "assets/audio/ok.wav").read_bytes() == wav,
              "通道侧 base64 写入的字节应与原字节一致")
        svc.release_instance(yid)

        # 21. 审查用途收窄(任务票 13):review 用途把同角色实例的可写集合限制到
        #     策略 review.restrict(evidence/)。审查实例只写审查记录与证据,碰不到
        #     待审成果;即使任务授权被放宽,purpose 层仍然封顶。
        svc.init_policy(
            project_root=project,
            roles={
                "producer": ["docs/mygamestudio/PROJECT.md"],
                "design": ["docs/mygamestudio/GAME_DESIGN.md"],
                "implement": ["src/**", "assets/**", "build/**",
                              "docs/mygamestudio/work/*/results/**",
                              "docs/mygamestudio/evidence/**"],
            },
            purposes={"production": None, "prototype": ["prototypes/**"],
                      "review": ["docs/mygamestudio/evidence/**"]},
        )
        rid, rtok = new_instance(svc, "implement",
                                 ["docs/mygamestudio/evidence/**"],
                                 purpose="review", task="T-review")
        res = svc.scope(rtok)
        check(res["decision"] == "allow" and res["purpose"] == "review",
              f"review 实例 scope 应成功并回读用途,实际 {res}")
        check(res["allowed"] == ["docs/mygamestudio/evidence/**"],
              f"review 实例有效范围应恰为 evidence/,实际 {res.get('allowed')}")
        res = svc.write(rtok, "docs/mygamestudio/evidence/review-run.md",
                        "# 审查记录\n", note="审查记录写入")
        check(res["decision"] == "allow",
              f"review 实例写 evidence/ 应成功,实际 {res}")
        for target, label in (
            ("src/player.js", "待审代码"),
            ("docs/mygamestudio/work/01-status/results/x.md", "任务结果"),
        ):
            res = svc.write(rtok, target, "OVERWRITE\n", note="越界尝试")
            check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
                  f"review 实例写{label}应被任务授权层拒绝,实际 {res}")
        # 放宽任务授权后 purpose 层仍封顶在 evidence/
        rid2, rtok2 = new_instance(svc, "implement",
                                   ["docs/mygamestudio/evidence/**", "src/**",
                                    "docs/mygamestudio/work/*/results/**"],
                                   purpose="review", task="T-review-wide")
        check(svc.scope(rtok2)["allowed"] == ["docs/mygamestudio/evidence/**"],
              "放宽授权后 review 实例有效范围仍应恰为 evidence/")
        before_review = code.read_bytes()
        res = svc.write(rtok2, "src/player.js", "OVERWRITE\n", note="越界尝试")
        check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
              f"放宽授权后 review 用途写 src 应被 purpose 层拒绝,实际 {res}")
        check(code.read_bytes() == before_review,
              "被拒后待审代码字节应保持不变")
        svc.release_instance(rid)
        svc.release_instance(rid2)

        # 22. 试玩用途收窄(任务票 14):playtest 用途把同角色实例的可写集合限制到
        #     策略 playtest.restrict(evidence/)。试玩实例只写试玩记录、证据及允许的
        #     测试运行状态,碰不到被试成果与任务记录;任务授权放宽时 purpose 层封顶;
        #     签发 CLI(mgsrt_admin.py)的用途白名单接受 playtest 并拒绝未知用途。
        svc.init_policy(
            project_root=project,
            roles={
                "producer": ["docs/mygamestudio/PROJECT.md"],
                "design": ["docs/mygamestudio/GAME_DESIGN.md"],
                "implement": ["src/**", "assets/**", "build/**",
                              "docs/mygamestudio/work/*/results/**",
                              "docs/mygamestudio/evidence/**"],
            },
            purposes={"production": None, "prototype": ["prototypes/**"],
                      "review": ["docs/mygamestudio/evidence/**"],
                      "playtest": ["docs/mygamestudio/evidence/**"]},
        )
        tid, ttok = new_instance(svc, "implement",
                                 ["docs/mygamestudio/evidence/**"],
                                 purpose="playtest", task="T-playtest")
        res = svc.scope(ttok)
        check(res["decision"] == "allow" and res["purpose"] == "playtest",
              f"playtest 实例 scope 应成功并回读用途,实际 {res}")
        check(res["allowed"] == ["docs/mygamestudio/evidence/**"],
              f"playtest 实例有效范围应恰为 evidence/,实际 {res.get('allowed')}")
        res = svc.write(ttok, "docs/mygamestudio/evidence/playtest-run.md",
                        "# 试玩记录\n", note="试玩记录写入")
        check(res["decision"] == "allow",
              f"playtest 实例写 evidence/ 应成功,实际 {res}")
        for target, label in (
            ("src/player.js", "被试代码"),
            ("build/main.js", "被试构建产物"),
            ("docs/mygamestudio/work/01-status/task.md", "任务记录"),
        ):
            if target == "build/main.js":
                (project / "build").mkdir(exist_ok=True)
                (project / "build/main.js").write_text("// BUILD\n")
            res = svc.write(ttok, target, "OVERWRITE\n", note="越界尝试")
            check(res["decision"] == "deny" and res["rule_stage"] == "task_grant",
                  f"playtest 实例写{label}应被任务授权层拒绝,实际 {res}")
        # 放宽任务授权后 purpose 层仍封顶在 evidence/
        tid2, ttok2 = new_instance(svc, "implement",
                                   ["docs/mygamestudio/evidence/**", "src/**",
                                    "build/**"],
                                   purpose="playtest", task="T-playtest-wide")
        check(svc.scope(ttok2)["allowed"] == ["docs/mygamestudio/evidence/**"],
              "放宽授权后 playtest 实例有效范围仍应恰为 evidence/")
        before_playtest = code.read_bytes()
        res = svc.write(ttok2, "src/player.js", "OVERWRITE\n", note="越界尝试")
        check(res["decision"] == "deny" and res["rule_stage"] == "purpose",
              f"放宽授权后 playtest 用途写 src 应被 purpose 层拒绝,实际 {res}")
        check(code.read_bytes() == before_playtest,
              "被拒后被试代码字节应保持不变")
        svc.release_instance(tid)
        svc.release_instance(tid2)

        # 22b. 签发 CLI 用途白名单(任务票 14):mgsrt_admin 接受 playtest,
        #      未知用途仍被拒绝(白名单演进,不是去掉校验)。
        import subprocess

        cli_root = root / "cli-runtime"
        cli_root.mkdir()
        spec_path = root / "policy-spec-14.json"
        spec_path.write_text(json.dumps({
            "project_root": str(project),
            "roles": {"implement": ["docs/mygamestudio/evidence/**"]},
            "purposes": {"playtest": ["docs/mygamestudio/evidence/**"]},
        }))
        admin = [sys.executable, "-B",
                 str(REPO_ROOT / "plugin" / "runtime" / "mgsrt_admin.py")]
        proc = subprocess.run(
            admin + ["--runtime-root", str(cli_root), "init-policy",
                     "--spec", str(spec_path)],
            capture_output=True, text=True)
        check(proc.returncode == 0, f"CLI init-policy 应成功,实际 {proc.stderr[-200:]}")
        proc = subprocess.run(
            admin + ["--runtime-root", str(cli_root), "create-instance",
                     "--role", "implement", "--task", "T-cli-playtest",
                     "--purpose", "playtest",
                     "--resource", "docs/mygamestudio/evidence/**",
                     "--ttl-mins", "5"],
            capture_output=True, text=True)
        check(proc.returncode == 0,
              "CLI create-instance --purpose playtest 应被白名单接受"
              f"(任务票 14),实际 {proc.stderr[-200:]}")
        try:
            payload = json.loads(proc.stdout)
            check(payload.get("ok") is True and payload.get("purpose") == "playtest",
                  f"CLI 签发应返回 playtest 用途实例,实际 {payload.get('purpose')}")
        except json.JSONDecodeError:
            check(False, "CLI create-instance 应输出 JSON")
        proc = subprocess.run(
            admin + ["--runtime-root", str(cli_root), "create-instance",
                     "--role", "implement", "--task", "T-cli-bad",
                     "--purpose", "playtestx",
                     "--resource", "docs/mygamestudio/evidence/**"],
            capture_output=True, text=True)
        check(proc.returncode != 0, "CLI 未知用途应被白名单拒绝")

        # 23. 占用回收(任务票 15):先撤销旧执行能力,再回收占用。
        #     活跃实例的占用不可回收(拒绝);释放/过期后才可回收;
        #     回收后新执行者可接管同一资源。
        race_root = root / "race-runtime"
        race_project = root / "race-project"
        (race_project / "docs/mygamestudio/work/15-race").mkdir(parents=True)
        race_svc = GateService(race_root)
        race_svc.init_policy(
            project_root=race_project,
            roles={"implement": ["docs/mygamestudio/work/15-race/**"]},
            purposes={"production": None},
        )
        target = "docs/mygamestudio/work/15-race/notes.md"

        def race_instance(task: str, ttl: int = 1800) -> tuple[str, str]:
            inst = race_svc.create_instance(role="implement", task=task,
                                            purpose="production",
                                            resources=["docs/mygamestudio/work/15-race/**"],
                                            ttl_seconds=ttl)
            return inst.instance_id, inst.token

        aid, atok = race_instance("T-hold")
        res = race_svc.write(atok, target, "HOLDER\n")
        check(res["decision"] == "allow", f"持有实例首写应成功,实际 {res}")
        bid, btok = race_instance("T-takeover")
        res = race_svc.write(btok, target, "TAKEOVER\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"占用期间新执行者写入应被拒,实际 {res}")
        # 活跃实例的占用不可回收:拒绝并保持占用
        result = race_svc.reclaim_locks(aid)
        check(result["ok"] is False and result.get("active") is True,
              f"活跃实例的占用回收应被拒绝,实际 {result}")
        res = race_svc.write(btok, target, "TAKEOVER\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              "拒绝回收后占用应保持,新执行者仍被拒")
        locks = race_svc.list_locks()
        check(target in locks.get("locks", {})
              and locks["locks"][target]["instance_id"] == aid,
              f"list_locks 应回报当前占用,实际 {locks}")
        # 释放(撤销执行能力)本身回收占用;再回收为幂等空操作
        race_svc.release_instance(aid)
        result = race_svc.reclaim_locks(aid)
        check(result["ok"] is True and result["reclaimed"] == 0,
              f"释放后重复回收应为幂等空操作,实际 {result}")
        res = race_svc.write(btok, target, "TAKEOVER\n")
        check(res["decision"] == "allow", f"释放后新执行者应可接管,实际 {res}")
        race_svc.release_instance(bid)

        # 24. 到期实例的悬挂占用:实例在有效期内取得占用后过期,
        #     令牌失效(写被拒)但占用记录悬挂;回收按到期放行。
        xid, xtok = race_instance("T-expire", ttl=1)
        res = race_svc.write(xtok, target, "EXPIRE\n")
        check(res["decision"] == "allow", f"短期实例首写应成功,实际 {res}")
        time.sleep(1.2)
        res = race_svc.write(xtok, target, "EXPIRE2\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "identity",
              f"过期令牌写入应被拒(identity),实际 {res}")
        kid, ktok = race_instance("T-takeover-expire")
        res = race_svc.write(ktok, target, "TAKEOVER2\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"过期实例的占用仍应阻塞新执行者,实际 {res}")
        result = race_svc.reclaim_locks(xid)
        check(result["ok"] is True and result["reclaimed"] >= 1,
              f"到期实例的占用回收应放行并释放,实际 {result}")
        res = race_svc.write(ktok, target, "TAKEOVER2\n")
        check(res["decision"] == "allow", f"回收后新执行者应可接管,实际 {res}")
        race_svc.release_instance(kid)
        result = race_svc.reclaim_locks("i-nonexistent")
        check(result["ok"] is False and result["found"] is False,
              f"未知实例回收应被拒,实际 {result}")

        # 24b. 释放流程中断缺口:release_instance 在登记与占用两次落盘之间
        #      崩溃会留下「已释放但仍持有占用」状态(直接构造该终态验证);
        #      再次 release 不再处理(found=False),reclaim_locks 补上回收。
        yid, ytok = race_instance("T-crashgap")
        res = race_svc.write(ytok, target, "GAP\n")
        check(res["decision"] == "allow", f"缺口演示实例首写应成功,实际 {res}")
        with race_svc._locked():
            records = race_svc._read_json("instances.json", [])
            for record in records:
                if record["instance_id"] == yid:
                    record["released"] = True
            race_svc._write_json("instances.json", records)
            # 模拟:instances.json 落盘后、locks.json 落盘前进程被杀
        res = race_svc.write(ytok, target, "GAP2\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "identity",
              "已释放实例的令牌应立即失效(持续进程不能再写)")
        zid, ztok = race_instance("T-takeover-gap")
        res = race_svc.write(ztok, target, "TAKEOVER3\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"中断缺口下占用仍悬挂,实际 {res}")
        release_result = race_svc.release_instance(yid)
        check(release_result["found"] is False,
              "再次 release 对已释放记录不再处理(found=False)")
        res = race_svc.write(ztok, target, "TAKEOVER3\n")
        check(res["decision"] == "deny",
              "再次 release 不应顺带回收悬挂占用(现状),由回收接缝负责")
        result = race_svc.reclaim_locks(yid)
        check(result["ok"] is True and result["reclaimed"] >= 1,
              f"回收接缝应补上中断缺口的占用回收,实际 {result}")
        res = race_svc.write(ztok, target, "TAKEOVER3\n")
        check(res["decision"] == "allow", f"缺口回收后新执行者应可接管,实际 {res}")
        race_svc.release_instance(zid)

        # 25. 真实并发竞争(任务票 15):两个独立进程经同一运行根同时写入同一
        #     资源——文件锁串行化后恰一个有效写入者,另一个 occupancy 拒绝;
        #     规范化路径(./ 与项目内符号链接别名)映射到同一占用;
        #     过期输入(expected_sha256 不符)被拒,不覆盖他人成果;
        #     独立资源并行写入互不阻塞。
        driver = root / "race_driver.py"
        driver.write_text(
            "import json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from mgs_runtime import GateService\n"
            "runtime_root, token, path, content, expected = sys.argv[2:]\n"
            "svc = GateService(runtime_root)\n"
            "res = svc.write(token, path, content,\n"
            "                expected_sha256=(expected or None))\n"
            "print(json.dumps(res))\n",
            encoding="utf-8")
        runtime_src = str(REPO_ROOT / "plugin" / "runtime")

        def race_proc(token: str, path: str, content: str, expected: str = ""):
            return subprocess.Popen(
                [sys.executable, "-B", str(driver), runtime_src,
                 str(race_root), token, path, content, expected],
                stdout=subprocess.PIPE, text=True)

        # 25a. 同一资源:两进程同时启动,恰一个 allow
        race_target2 = "docs/mygamestudio/work/15-race/race.md"
        cid, ctok = race_instance("T-race-a", ttl=1800)
        did, dtok = race_instance("T-race-b", ttl=1800)
        p1 = race_proc(ctok, race_target2, "FROM-A\n")
        p2 = race_proc(dtok, race_target2, "FROM-B\n")
        out1 = json.loads(p1.communicate(timeout=30)[0])
        out2 = json.loads(p2.communicate(timeout=30)[0])
        decisions = sorted([out1["decision"], out2["decision"]])
        check(decisions == ["allow", "deny"],
              f"并发竞争应恰有一个有效写入者,实际 {out1.get('decision')}/{out2.get('decision')}")
        denied = out1 if out1["decision"] == "deny" else out2
        allowed = out2 if out1["decision"] == "deny" else out1
        check(denied["rule_stage"] == "occupancy",
              f"竞争失败方应被占用拒绝,实际 {denied}")
        check(allowed["rule_stage"] == "granted", f"竞争胜者应为 granted,实际 {allowed}")
        final_content = (race_project / race_target2).read_text()
        check(final_content in ("FROM-A\n", "FROM-B\n"),
              f"最终内容应恰为胜者写入,实际 {final_content!r}")

        # 25b. 规范化别名:竞争胜者持有占用后,经 ./ 折叠路径与项目内符号
        #      链接别名写入同一资源,仍被占用拒绝(不能靠别名绕过单写入者)。
        winner_token = ctok if out1["decision"] == "allow" else dtok
        alias_dot = "docs/mygamestudio/work/15-race/./race.md"
        res = race_svc.write(winner_token, alias_dot, "ALIAS\n")
        check(res["decision"] == "allow",
              "同一实例经 ./ 别名写自身占用资源应成功(同一占用者)")
        loser_token = dtok if out1["decision"] == "allow" else ctok
        res = race_svc.write(loser_token, alias_dot, "ALIAS\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"他方经 ./ 别名写被占资源应被拒,实际 {res}")
        (race_project / "docs/mygamestudio/work/alias15").symlink_to("15-race")
        res = race_svc.write(loser_token,
                             "docs/mygamestudio/work/alias15/race.md", "ALIAS\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"项目内符号链接别名写被占资源应被拒(占用按规范化标识),实际 {res}")

        # 25c. 过期输入:释放胜者后,新执行者持过期的 expected_sha256 写入
        #      应被 version 拒绝,不覆盖他人已写入成果;以实际内容指纹重试才成功。
        race_svc.release_instance(cid)
        race_svc.release_instance(did)
        final_content = (race_project / race_target2).read_text()
        eid, etok = race_instance("T-stale")
        stale = hashlib.sha256(b"never-existed").hexdigest()
        res = race_svc.write(etok, race_target2, "STALE\n", expected_sha256=stale)
        check(res["decision"] == "deny" and res["rule_stage"] == "version",
              f"过期输入应被版本校验拒绝,实际 {res}")
        check((race_project / race_target2).read_text() == final_content,
              "被拒后他人成果字节应保持不变")
        current = hashlib.sha256(
            (race_project / race_target2).read_bytes()).hexdigest()
        res = race_svc.write(etok, race_target2, "REFRESH\n",
                             expected_sha256=current)
        check(res["decision"] == "allow", f"按实际内容版本核对后写入应成功,实际 {res}")

        # 25d. 独立资源并行:两进程同时写不同资源,互不阻塞
        fid, ftok = race_instance("T-par-a")
        gid, gtok = race_instance("T-par-b")
        p1 = race_proc(ftok, "docs/mygamestudio/work/15-race/par-a.md", "PA\n")
        p2 = race_proc(gtok, "docs/mygamestudio/work/15-race/par-b.md", "PB\n")
        out1 = json.loads(p1.communicate(timeout=30)[0])
        out2 = json.loads(p2.communicate(timeout=30)[0])
        check(out1["decision"] == "allow" and out2["decision"] == "allow",
              f"独立资源并行写入应互不阻塞,实际 {out1.get('decision')}/{out2.get('decision')}")
        race_svc.release_instance(fid)
        race_svc.release_instance(gid)

        # 26-33. 任务票 17:mgs_remote 受控远端任务操作(本地替身传输层)
        remote_record_section(root)

        # 34+. 审查修复批(票 02-fix):R1–R4 反例固化
        review_fix_section(root)

        # 35+. 审查修复批(票 01-fix):通道侧反例固化(说明三路一致/
        #      不确定结果如实回报)
        records_review_fix_section(root)

        # 36+. 第二轮审查修复批(票 review2-01):SP-1 在途 CONFIG 授权
        #      撤销的远端临界区反例固化
        review2_sp1_section(root)

        # 37+. 第二轮审查修复批(票 review2-02):SP-2 评论已发布而索引
        #      更新超时的部分成功误报,通道级反例固化
        review2_sp2_section(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if FAILURES:
        print(f"FAIL ({len(FAILURES)} 项):")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("OK: 受控写入服务确定性检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
