#!/usr/bin/env python3
"""GitHub 后端切换迁移与远端交接(票 20;从 mgs_github 按职责移出)。

把「后端切换迁移清单、切换执行与远端交接基线可达核对」这组独立职责从
业务适配器 ``mgs_github`` 移到本 module:适配器只保留读、写与执行分发,
迁移/交接的开清单、确认后 apply 与只读交接核对集中在此处,既有公开函数
签名、返回字段、错误语义与只读/不越权约束逐条保持。

职责:
- ``handover_baseline_check``:每份核心基线的本地存在性与已发布引用的
  实际可达检查(未执行检查按未验证/不可达回报);
- ``plan_backend_switch``:确认前的只读迁移清单(任务映射、保留方案、
  需确认项、交接基线可达核对);
- ``apply_backend_switch``:执行**已确认**的切换,只做目标侧创建与材料
  产出,不删除旧记录、不直接改写项目 CONFIG,目标为 GitHub 时再核对授权;
- ``_published_refs`` / ``_ref_check_url`` / ``_emitted_config_text``:
  上述入口的文本与产出助手。

依赖纪律:只依赖中性记录 module ``mgs_record_model``、来源 module
``mgs_record_source``、Issue 形态 module ``mgs_github_issue``(仓库坐标/
授权核对)与传输接缝 ``mgs_github_transport``;构造适配器时按既有模式在
函数内延迟导入 ``mgs_github``(避免与适配器的重导出形成加载期循环)。
本模块不发起真实远端写入(任务创建走注入 transport/替身)。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mgs_github_issue  # noqa: E402
import mgs_record_model  # noqa: E402
import mgs_record_source  # noqa: E402
from mgs_github_issue import parse_repo_location  # noqa: E402
from mgs_github_transport import (  # noqa: E402
    GithubRecordsError, TransportError, repo_str)
from mgs_record_model import edit_body  # noqa: E402,F401

WRITE_OP = mgs_record_source.WRITE_OP
GITHUB_BACKEND = "github-issues"
_authorization_for = mgs_github_issue.authorization_for


def _published_refs(config_text: str) -> dict[str, str]:
    """解析 CONFIG 外部访问行中的已发布基线引用
    (`已发布基线引用:<文件>=<url或commit@版本>`,分号分隔)。"""

    refs: dict[str, str] = {}
    match = re.search(r"已发布基线引用\s*[:：]\s*(.+)", config_text or "")
    if not match:
        return refs
    for item in re.split(r"[;；,，]", match.group(1)):
        if "=" not in item:
            continue
        name, ref = item.split("=", 1)
        refs[name.strip()] = ref.strip()
    return refs


def _ref_check_url(ref: str) -> str | None:
    """引用 → 可经传输层检查的绝对 URL。

    `url@版本` 形态剥去版本后缀再检查;非 http(s) 引用(如本地 commit 串)
    返回 None——无法实际检查的引用形态不宣称可达。
    """

    if not ref.startswith(("http://", "https://")):
        return None
    return re.sub(r"@[A-Za-z0-9._-]+$", "", ref)


def handover_baseline_check(project_root: Path | str,
                            config_rel: str = mgs_record_source.DEFAULT_CONFIG_REL,
                            *, transport=None) -> dict:
    """远端交接核对基线引用可达(《工作记录合同》:本地尚未发布的基线可供
    本机执行者引用,但不得声称远端执行者已可访问)。

    每份核心基线:本地存在性与当前版本 + 已发布引用的**实际可达检查**。
    可达性结论只能来自实际执行的检查(审查修复票 01/S4):经传输层 GET
    引用地址,2xx 才判可达;未执行检查(无通道/上游不可用)、检查失败或
    引用形态不可检查,一律按未验证/不可达回报——引用存在不等于检查通过。
    ok 仅在全部核心基线经检查可达时为 True(交接前须补发布引用或明确限制)。
    """

    root = Path(project_root)
    config = mgs_record_source.load_config(root, config_rel)
    refs = _published_refs((root / config_rel).read_text(encoding="utf-8"))
    grouped = mgs_record_model._core_rows(config["docmap"])
    docs: list[dict] = []
    for key in ("goal", "design", "tech"):
        for row in grouped[key]:
            path = root / row["path"]
            published = (refs.get(row["path"]) or refs.get(Path(row["path"]).name))
            version = None
            if path.is_file():
                version_match = re.search(r"基线版本\s*[:：]\s*v(\d+)",
                                          path.read_text(encoding="utf-8"))
                version = f"v{version_match.group(1)}" if version_match else None
            reachable = False
            if not published:
                note = ("本地未发布资料:远端执行者不可访问,不得宣称已可远端"
                        "访问;发布资料仍需对应授权")
            else:
                url = _ref_check_url(published)
                if transport is None:
                    note = (f"已记录引用:{published};未执行可达检查(未提供"
                            "检查通道)——引用存在不等于检查通过,未验证按"
                            "不可达处理")
                elif url is None:
                    note = (f"已记录引用:{published};引用形态无法经传输层"
                            "检查,未验证按不可达处理")
                else:
                    try:
                        # 可达探测不带凭据:引用地址可能是任意第三方主机,
                        # API 令牌不得随探测外发(审查修复票 01/Spec 复查)
                        status, _data = transport.request("GET", url, auth=False)
                    except TransportError as exc:
                        note = (f"已记录引用:{published};可达检查未完成"
                                f"({exc})——不可达/未验证,不宣称可达")
                    else:
                        if 200 <= int(status) < 300:
                            reachable = True
                            note = (f"已发布引用:{published}(实际检查 HTTP "
                                    f"{status},远端执行者经此引用访问)")
                        else:
                            note = (f"已记录引用:{published};实际检查 HTTP "
                                    f"{status}——引用不可达,先补发布或修正引用")
            docs.append({
                "path": row["path"], "content": row["content"], "role": row["role"],
                "local_exists": path.is_file(), "version": version,
                "published_ref": published,
                "remote_reachable": reachable,
                "note": note,
            })
    ok = all(entry["remote_reachable"] for entry in docs)
    return {"ok": ok, "docs": docs,
            "note": ("本地尚未发布的基线可以供本机执行者引用,但必须标明资料"
                     "位置和版本;不能声称远端执行者已可访问。准备远端交接时"
                     "确认引用可达,发布资料仍需对应授权。可达性结论只能来自"
                     "实际执行的检查;未执行检查(含上游不可用)按未验证/"
                     "不可达回报,引用存在不等于检查通过。")}


def plan_backend_switch(project_root: Path | str, *, target: str,
                        repo: str | None = None, transport=None,
                        cache_dir: Path | str | None = None) -> dict:
    """后端切换迁移清单(确认前只读):任务映射、保留方案、需确认项与
    交接基线可达核对。调用方确认后才执行 apply;apply 不直接改项目文件。
    """

    import mgs_github  # noqa: PLC0415 - 延迟导入避免加载期循环

    if target not in ("github-issues", "local-markdown"):
        raise GithubRecordsError(f"未知目标后端 {target!r}")
    root = Path(project_root)
    config = mgs_record_source.load_config(root)
    if config["backend"] == target:
        raise GithubRecordsError(f"当前后端已是 {target},无需切换")
    if target == "github-issues":
        target_repo = parse_repo_location(repo or config["task_root"])
        # 本地任务读取直接依赖本地来源 adapter(不反向经查询入口);
        # 本次已加载配置只供本次列举,不重读 CONFIG。
        tasks = mgs_record_source.local_list_tasks(root, config)
        task_items = [{
            "identity": task["identity"], "title": task["title"],
            "triage": task["triage"], "progress": task["progress"],
            "request": task["request"],
            "source_ref": f"local:{config['task_root']}/{task['identity']}/task.md",
            "target_ref": (f"github:{target_repo['host']}/{target_repo['owner']}/"
                           f"{target_repo['repo']}/issues(身份保持 {task['identity']})"),
        } for task in tasks]
    else:
        target_repo = None
        backend = mgs_github.GithubBackend(config, transport, cache_dir)
        tasks = backend.fetch_tasks()["tasks"]
        task_items = [{
            "identity": task["identity"], "title": task["title"],
            "triage": task["triage"], "progress": task["progress"],
            "request": task["request"],
            "source_ref": (f"github:{config['repo']['host']}/{config['repo']['owner']}/"
                           f"{config['repo']['repo']}/issues/{task['issue_number']}"),
            "target_ref": (f"local:{mgs_record_source.DEFAULT_TASK_ROOT}/"
                           f"{task['identity']}/task.md(身份保持)"),
        } for task in tasks]
    if not task_items:
        raise GithubRecordsError("当前后端没有可迁移的任务;切换空账本前先人工确认")
    authorized = _authorization_for(
        {**config, "repo": target_repo}, WRITE_OP)[0] if target_repo else False
    return {
        "from": config["backend"], "to": target,
        # repo = 目标位置(github 目标=仓库坐标;本地目标=本地任务根),与
        # CONFIG 任务根、文件落点、返回路径共用同一来源(审查修复票 01/S3)
        "repo": (repo_str(target_repo) if target_repo
                 else mgs_record_source.DEFAULT_TASK_ROOT),
        # 旧位置 = 迁移源的实际任务位置(github 源=旧仓库坐标;本地源=旧任务根)
        "old_position": config["task_root"],
        "project_root": str(root),
        "old_config_text": (root / config["config_path"]).read_text(encoding="utf-8"),
        "tasks": task_items,
        "write_authorized": authorized,
        "retention": [
            f"旧记录({config['backend']})全部保留为只读历史,不删除、不改写;",
            "切换生效后旧位置不再是当前任务来源,不得在其上继续安排工作"
            "(不形成两套可独立修改的当前任务账本);",
            "身份映射(本地身份 ↔ Issue 号)随新 CONFIG 留档,追溯旧记录时使用。",
        ],
        "confirmations": [
            "确认切换当前任务来源为新后端(此后唯一当前来源);",
            "确认对目标仓库的远端写入授权并已按 "
            "`host/owner/repo:issues-write(说明)` 记入 CONFIG——仅选择后端"
            "不构成授权" + ("" if authorized else "(当前 CONFIG 尚未记录,apply 前必须补)"),
            "确认远端交接的基线引用可达性(handover 检查);未发布本地资料"
            "不得宣称远端已可访问。",
        ],
        "baseline_handover": handover_baseline_check(root, transport=transport)["docs"],
        "labels": config["labels"],
    }


def _emitted_config_text(plan: dict, old_config_text: str) -> str:
    """切换后的 CONFIG 内容:唯一当前来源指向新后端,旧位置标只读历史,
    标签映射与文档映射沿用(核心文档位置不随后端切换变化)。

    当前位置取 plan['repo'](目标位置),历史位置取 plan['old_position']
    (迁移源实际位置)——与新 CONFIG 任务根、文件落点、返回路径同源
    (审查修复票 01/S3)。
    """

    lines: list[str] = ["# 协作配置(后端切换)", "",
                        "维护责任:制作统筹。采用依据:已确认的后端切换迁移清单。", "",
                        "## 任务来源", "",
                        f"- 后端:{plan['to']}"]
    if plan["to"] == "github-issues":
        lines.append(f"- 当前位置:{plan['repo']}")
        lines.append("- 任务读取规则:GitHub Issues 后端约定(Issue 正文承载"
                     "任务说明,评论承载结果)")
    else:
        lines.append(f"- 当前位置:{plan['repo']}(每任务一目录,task.md 为"
                     "工作请求与状态)")
        lines.append("- 任务读取规则:本地 Markdown 后端约定")
    # 旧位置兜底:旧清单无 old_position 字段时按方向推断(github 目标的
    # 旧位置是本地任务根;本地目标的旧位置沿用清单 repo 字段的旧语义)
    old_position = plan.get("old_position") or (
        mgs_record_source.DEFAULT_TASK_ROOT if plan["to"] == "github-issues"
        else plan["repo"])
    lines.append("- 历史任务位置(只读历史):" + old_position
                 + "(切换前账本,只作历史追溯,不再是当前任务来源)")
    for line in old_config_text.splitlines():
        if line.startswith("- 外部连接引用及已确认操作范围"):
            lines.append(line)
    lines += ["", "## 标签映射", "", "| 语义 | 项目标签 |", "| --- | --- |"]
    for canon, project in plan["labels"].items():
        lines.append(f"| {canon} | {project} |")
    lines += ["", "## 文档映射", "", "| 内容 | 当前权威位置 | 维护角色 |",
              "| --- | --- | --- |"]
    section = ""
    for line in old_config_text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section == "文档映射" and line.startswith("|") \
                and not set(line.strip()) <= set("|-: ") \
                and not line.startswith("| 内容"):
            lines.append(line)
    lines += ["", "## 身份映射(切换留档)", "",
              "本地身份 → Issue 号(或本地路径)见 identity-map.json;身份保持不变。",
              ""]
    return "\n".join(lines)


def apply_backend_switch(plan_path: Path | str, *, confirmed: bool,
                         emit_dir: Path | str, project_root: Path | str,
                         transport=None, cache_dir: Path | str | None = None) -> dict:
    """执行**已确认**的切换:只做目标侧创建与材料产出。

    - 不删除、不改写旧记录(保留只读历史);
    - 不直接改写项目 CONFIG:新 CONFIG 内容产出到 emit_dir/CONFIG.md,
      由经确认的应用步骤(统筹经 mgs-gate 受控通道)写入,保证唯一当前来源;
    - 目标为 GitHub 时,要求当前项目 CONFIG 已记录目标仓库的 issues-write
      授权(apply 侧再核对一次,不自我授权)。
    """

    import mgs_github  # noqa: PLC0415 - 延迟导入避免加载期循环

    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    if not confirmed:
        raise GithubRecordsError("迁移清单未经确认(confirmed=False),不执行切换")
    root = Path(project_root)
    current = mgs_record_source.load_config(root)
    emit = Path(emit_dir)
    emit.mkdir(parents=True, exist_ok=True)
    created = 0
    mapping: dict[str, dict] = {}
    if plan["to"] == "github-issues":
        target_repo = parse_repo_location(plan["repo"])
        allowed, _note = _authorization_for({**current, "repo": target_repo},
                                            WRITE_OP)
        if not allowed:
            raise GithubRecordsError(
                f"项目 CONFIG 尚未对 {plan['repo']} 记录 issues-write 授权;"
                "迁移清单确认后须先按 `host/owner/repo:issues-write(说明)` 更新"
                " CONFIG(经确认的应用步骤),apply 不自我授权")
        backend = mgs_github.GithubBackend({**current, "repo": target_repo,
                                            "backend": GITHUB_BACKEND},
                                           transport, cache_dir)
        results = []
        for item in plan["tasks"]:
            outcome = backend.create_task(
                item["identity"], item["title"], item["request"],
                triage=item["triage"], progress=item["progress"])
            results.append({"identity": item["identity"], **{
                key: outcome.get(key)
                for key in ("created", "adopted", "issue_number", "published")}})
            if outcome.get("created") or outcome.get("adopted"):
                created += 1
                mapping[item["identity"]] = {
                    "github_issue": outcome.get("issue_number"),
                    "source_ref": item["source_ref"]}
        (emit / "identity-map.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        result = {"created": created, "results": results, "emit_dir": str(emit)}
    else:
        for item in plan["tasks"]:
            body = mgs_github_issue.build_task_body(
                item["title"], item["identity"], item["triage"],
                item["progress"], item["request"])
            rel = (f"{mgs_record_source.DEFAULT_TASK_ROOT}/"
                   f"{item['identity']}/task.md")
            path = emit / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            mapping[item["identity"]] = {"local_path": rel,
                                         "source_ref": item["source_ref"]}
            created += 1
        (emit / "identity-map.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        # 返回的产出目录 = 实际落盘根(任务文件与 CONFIG 都在其下),
        # 与计划目标、CONFIG 任务根同源(审查修复票 01/S3)
        result = {"created": created, "emit_dir": str(emit)}
    (emit / "CONFIG.md").write_text(
        _emitted_config_text(plan, plan.get("old_config_text", "")),
        encoding="utf-8")
    result["config_emitted"] = str(emit / "CONFIG.md")
    result["note"] = ("apply 只创建目标侧任务并产出新 CONFIG 内容;项目 CONFIG "
                      "由经确认的应用步骤经 mgs-gate 写入(唯一当前来源),"
                      "旧记录保留为只读历史,身份映射已留档。")
    return result
