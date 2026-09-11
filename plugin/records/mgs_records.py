#!/usr/bin/env python3
"""MyGameStudio 本地 Markdown 任务后端:统一回读接口(任务票 04,票 08/15 扩展,
票 17 增加对 github-issues 后端的分发与写操作 CLI)。

对应设计《工作记录合同》「后端接口」一节:读取配置、列出任务、读取任务与结果、
回读核验(票 04);关系解析与循环检测、当前可开工集合(票 08);核心基线内容
指纹核对与受影响任务识别(票 15);GitHub Issues 后端同语义适配与切换迁移
(票 17,适配器在 mgs_github.py)。调用方只使用 CONFIG.md 配置后的入口,
不硬编码 work/ 或 .scratch/(配置路径可显式传入,默认值来自
《项目目录模板》的默认布局)。

边界:
- 本地 Markdown 后端:本模块只做读取与核验,不提供写入。项目内写入一律经
  运行保障受控通道(mgs-gate 的 mgs_write)完成;本模块的核验结果针对实际
  落盘内容。
- GitHub Issues 后端(任务票 17):读取经 mgs_github 传输层(远端不可用回
  注明时间与来源的缓存,不静默切本地);远端写操作(创建/安排更新/结果追加/
  关系/分流/关闭)先核对 CONFIG 中明确到仓库的 issues-write 授权,经
  `--api-base`/MGS_GH_API_BASE 可指向本地替身;会话内工作实例的远端写入走
  mgs-gate 的 mgs_remote 受控通道,本 CLI 写入口供可信调度侧与已授权操作者
  使用。真实远端写入仅在明确授权的测试仓库执行(票 17 保留待办)。
- 未实现的其他后端:明确报不支持,不静默降级。
- 开工集合是「记录可核对的开工条件」判断,不是授权:ready-for-agent
  不等于依赖已完成或已获全部写入授权,开工前仍需按任务允许修改范围与
  运行保障核对授权(startable_tasks 输出附此提示)。

用法:
  mgs_records.py config --project <项目根> [--config <CONFIG相对路径>]
  mgs_records.py list  --project <项目根> [--config <CONFIG相对路径>] [--api-base URL] [--cache-dir DIR]
  mgs_records.py show  --project <项目根> --task <任务身份> [--config ...]
  mgs_records.py deps  --project <项目根> [--config <CONFIG相对路径>]
  mgs_records.py ready --project <项目根> [--config <CONFIG相对路径>]
  mgs_records.py baseline --project <项目根> [--config <CONFIG相对路径>]
  mgs_records.py verify --project <项目根> [--config <CONFIG相对路径>]
  GitHub 后端写操作(任务票 17,需 CONFIG issues-write 授权):
  mgs_records.py create|update|append-result|set-triage|set-relations|
                set-parent|close|publish-drafts|switch-plan|switch-apply|handover ...
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# 共同记录语义(错误身份、正文规则与纯记录核验)的唯一定义在
# mgs_record_model;本模块按现有公开名字重新导出,调用方定位不变。
from mgs_record_model import (  # noqa: E402  (路径调整后导入)
    CANONICAL_LABELS, CORE_DOC_KEYS, IDENTITY_RE, PLAN_REQUEST_KEYS,
    RecordsError, TASK_REQUEST_KEYS, _bullets, _core_rows, _field,
    _find_cycles, _parse_dep_ids, _sections, check_item, dependency_problems,
    docmap_checks, label_mapping_checks, parse_task_body, task_core_problems)

# 协作配置与本地任务来源的唯一定义在 mgs_record_source:本模块(查询组织)
# 从这里取配置、本地列举与按目录读取,并重导出既有公开名字;GitHub adapter
# 同样直接依赖该来源,不再反向调用本模块。
from mgs_record_source import (  # noqa: E402
    DEFAULT_CONFIG_REL, DEFAULT_TASK_ROOT, SUPPORTED_BACKENDS, _task_root,
    load_config, load_config_document, local_list_tasks, local_read_task)

# 错误身份唯一性由 mgs_record_model 的 RecordsError 单一定义保证(脚本与
# 模块导入同一类),不再需要把 __main__ 注册进 sys.modules 的临时身份补偿。

READY_NOTE = ("可开工=分流 ready 且记录字段完整且未完成依赖为空;这是开工条件核对,"
              "不等于依赖已全部完成或已获全部写入授权——开工前按任务「允许修改范围」"
              "与运行保障核对授权;能力与授权以实际执行环境为准。")


# ---------- 逻辑操作(公开接缝) ----------

def _local_config(project_root: Path | str, config_rel: str) -> dict:
    """读取配置并确认本地后端(未实现/非本地后端保持原有错误表达)。"""

    config = load_config(project_root, config_rel)
    if config["backend"] != "local-markdown":
        if config["backend"] == "github-issues":
            raise RecordsError(
                "github-issues 后端不使用本地任务目录(统一接口经 GitHub 后端"
                "适配器读取远端;不静默回退本地 work/ 目录)")
        raise RecordsError(
            f"后端 {config['backend']} 未实现(首版支持 local-markdown 与 "
            "github-issues;未实现的后端不声称可用)")
    return config


def _github_backend_for(config: dict, *, transport=None,
                        api_base: str | None = None,
                        cache_dir: Path | str | None = None):
    """由本次已解析配置构造 GitHub adapter(不再重读 CONFIG)。"""

    import mgs_github  # noqa: PLC0415 - 延迟导入避免循环依赖

    if config["backend"] != "github-issues":
        raise RecordsError(f"当前后端为 {config['backend']},不是 github-issues")
    if transport is None:
        transport = mgs_github.UrllibTransport(
            api_base=mgs_github.api_base_for(config, api_base),
            token=mgs_github.token_from_env())
    return mgs_github.GithubBackend(config, transport, cache_dir)


def github_backend(project_root: Path | str, config_rel: str = DEFAULT_CONFIG_REL,
                   *, transport=None, api_base: str | None = None,
                   cache_dir: Path | str | None = None):
    """构建 GitHub Issues 后端适配器(公开接缝;transport 供测试注入替身)。"""

    config = load_config(project_root, config_rel)
    return _github_backend_for(config, transport=transport, api_base=api_base,
                               cache_dir=cache_dir)


class _Reading:
    """一次顶层读取的内部载体:配置原文、配置、任务集合与读取元信息。

    只在本次调用内存在,不成为公共参数或返回对象;下一次顶层调用重新
    读取,不复用。它保证「本次不在隐式重取任务集合后混合计算」,但不
    承诺多个文件、远端详情与基线处于同一事务时刻。
    """

    __slots__ = ("config", "config_text", "tasks", "fetch_meta")

    def __init__(self, config: dict, config_text: str, tasks: list[dict],
                 fetch_meta: dict) -> None:
        self.config = config
        self.config_text = config_text
        self.tasks = tasks
        self.fetch_meta = fetch_meta


def _read_workspace(project_root: Path | str, config_rel: str, *,
                    transport=None, api_base: str | None = None,
                    cache_dir: Path | str | None = None) -> _Reading:
    """顶层读取一次:CONFIG 原文一次;需要任务集合时获取一次。

    本地每份 task.md 读取一次,GitHub 全量任务集合获取一次。任务集合保留
    来源顺序(本地目录顺序、GitHub list 原后端顺序),依赖与可开工判断都
    从这一份结果推导,不再回调重新获取任务的公开入口。读取元信息(是否
    缓存、抓取时间与来源)随载体传递到顶层结果——离线回缓存与在线当前
    确认由此可区分(审查修复票 01/S5)。
    """

    root = Path(project_root)
    config, config_text = load_config_document(root, config_rel)
    backend = config["backend"]
    if backend == "local-markdown":
        tasks = local_list_tasks(root, config)
        fetch_meta = {
            "cached": False,
            "fetched_at": _dt.datetime.now().astimezone().isoformat(
                timespec="seconds"),
            "source": {"backend": "local-markdown",
                       "task_root": config["task_root"]}}
        return _Reading(config, config_text, tasks, fetch_meta)
    if backend == "github-issues":
        payload = _github_backend_for(
            config, transport=transport, api_base=api_base,
            cache_dir=cache_dir).fetch_tasks()
        fetch_meta = {"cached": bool(payload.get("cached")),
                      "fetched_at": payload.get("fetched_at"),
                      "source": payload.get("source")}
        if fetch_meta["cached"]:
            fetch_meta["cache_note"] = payload.get("note", "")
        return _Reading(config, config_text, payload["tasks"], fetch_meta)
    raise RecordsError(
        f"后端 {backend} 未实现(首版支持 local-markdown 与 github-issues)")


def list_tasks(project_root: Path | str, config_rel: str = DEFAULT_CONFIG_REL,
               *, transport=None, api_base: str | None = None,
               cache_dir: Path | str | None = None) -> list[dict]:
    """列出任务身份、标题、分流与进度(经 CONFIG 解析任务源,不硬编码)。

    github-issues 后端经远端适配器列出(离线时返回任务级 cached_read 标注);
    本地后端委托 mgs_record_source 的本地 adapter,按目录顺序列举。
    """

    root = Path(project_root)
    config = load_config(root, config_rel)
    if config["backend"] == "github-issues":
        payload = github_backend(root, config_rel, transport=transport,
                                 api_base=api_base,
                                 cache_dir=cache_dir).fetch_tasks()
        tasks = payload["tasks"]
        if payload.get("cached"):
            for task in tasks:
                task["cached_read"] = True
        tasks.sort(key=lambda task: task["identity"])
        return tasks
    if config["backend"] != "local-markdown":
        raise RecordsError(
            f"后端 {config['backend']} 未实现(首版支持 local-markdown 与 github-issues)")
    return local_list_tasks(root, config)


def read_task(project_root: Path | str, task_id: str,
              config_rel: str = DEFAULT_CONFIG_REL, *, transport=None,
              api_base: str | None = None,
              cache_dir: Path | str | None = None) -> dict:
    """读取单个任务:头部字段、请求、小节与结果清单。"""

    root = Path(project_root)
    config = load_config(root, config_rel)
    if config["backend"] == "github-issues":
        return github_backend(root, config_rel, transport=transport,
                              api_base=api_base,
                              cache_dir=cache_dir).read_task(task_id)
    if config["backend"] != "local-markdown":
        raise RecordsError(
            f"后端 {config['backend']} 未实现(首版支持 local-markdown 与 github-issues)")
    return local_read_task(root, config, task_id)


# ---------- 关系解析与开工集合(任务票 08) ----------
# _parse_dep_ids / _find_cycles 的唯一定义在 mgs_record_model(共同记录语义),
# 本模块与 GitHub adapter 共用;此处不再重复定义。

def _dependency_graph(tasks: list[dict]) -> dict:
    """由一份已取得的任务集合生成依赖关系:边、未解析引用与循环。

    纯函数:不自行再次获取任务,供 deps 与 ready 在同一个已取集合上复用
    (票 04:一次查询的依赖与任务状态不混用两次读取结果)。任务集合的
    原始顺序决定 edges 的插入顺序,调用方各自的排序不受影响。
    """

    by_id = {task["identity"]: task for task in tasks}
    edges: dict[str, list[str]] = {}
    unresolved: list[dict] = []
    for task in tasks:
        deps = _parse_dep_ids(task["request"].get("依赖", ""))
        edges[task["identity"]] = deps
        for dep in deps:
            if dep not in by_id:
                unresolved.append({"identity": task["identity"], "dep": dep})
    cycles = _find_cycles(edges)
    return {"edges": edges, "unresolved": unresolved, "cycles": cycles,
            "ok": not unresolved and not cycles}


def task_dependencies(project_root: Path | str,
                      config_rel: str = DEFAULT_CONFIG_REL, *,
                      transport=None, api_base: str | None = None,
                      cache_dir: Path | str | None = None) -> dict:
    """解析任务依赖关系:边、未解析引用与循环(关系可解析且无循环为 ok)。

    双后端同语义:本地从 work/ 解析,github-issues 从远端任务正文解析
    (「依赖」字段可写 `#Issue号 身份` 或直接写身份,均按身份核对)。
    本次调用只取一份任务集合,依赖由该集合生成。
    """

    reading = _read_workspace(project_root, config_rel, transport=transport,
                              api_base=api_base, cache_dir=cache_dir)
    return _dependency_graph(reading.tasks)


def _doc_baseline_versions(root: Path, config: dict) -> dict[str, str]:
    """按文档映射建立可引用文档的当前逻辑版本表(如 GAME_DESIGN → "v2")。"""

    versions: dict[str, str] = {}
    for row in config["docmap"]:
        path = root / row["path"]
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        match = re.search(r"基线版本\s*[:：]\s*v(\d+)", text)
        if match:
            versions[row["path"]] = f"v{match.group(1)}"
            stem = Path(row["path"]).stem
            versions.setdefault(stem, f"v{match.group(1)}")
            versions.setdefault(str(Path(row["path"]).name), f"v{match.group(1)}")
    return versions


_BASELINE_REF_RE = re.compile(
    r"([A-Za-z0-9_./-]+\.md|[A-Z][A-Z0-9_]+)\s*[（(]?\s*[vV](\d+)")


def _baseline_drifts(versions: dict[str, str], value: str) -> list[str]:
    """核对「输入与基线」中的文档版本引用与当前基线版本表,报告漂移。"""

    drifts: list[str] = []
    for name, ref in _BASELINE_REF_RE.findall(value or ""):
        actual = versions.get(name) or versions.get(Path(name).stem)
        if actual and actual != f"v{ref}":
            drifts.append(f"基线版本漂移:{name} 当前 {actual},任务引用 v{ref}")
    return drifts


def _longest_common_text(a: str, b: str) -> str:
    """两段文本的最长公共子串(短语能力重叠判断用,短字符串)。"""

    best = ""
    for start in range(len(a)):
        for end in range(start + len(best) + 1, len(a) + 1):
            piece = a[start:end]
            if piece in b:
                best = piece
    return best


_CAPABILITY_NEGATION_RE = re.compile(r"不需要|无需|不涉及|不依赖|不使用|没有|"
                                     r"已就绪|已具备|均已|暂不需要")


def _capability_gaps(config_text: str, phrases: str) -> list[str]:
    """「所需能力」短语命中 CONFIG「尚未就绪的能力」说明时,报告能力未就绪。

    否定式表述(如「本任务不需要音频制作能力」「所需能力均已就绪」)不视为
    命中——记录在说该缺口不影响本任务(任务票 08 依真实拆单轮反馈补上)。
    """

    match = re.search(r"尚未就绪的能力及影响\s*[:：]\s*(.+)", config_text or "")
    notready = (match.group(1).strip() if match else "")
    if not notready or notready in ("无", "无。"):
        return []
    gaps: list[str] = []
    for phrase in re.split(r"[,，、;；/]|以及|和|与", phrases or ""):
        phrase = phrase.strip()
        if len(phrase) < 2 or _CAPABILITY_NEGATION_RE.search(phrase):
            continue
        overlap = _longest_common_text(phrase, notready)
        if len(overlap) >= 2 and any("\u4e00" <= ch <= "\u9fff" for ch in overlap):
            gaps.append(f"能力未就绪:{phrase}(命中 CONFIG 尚未就绪能力说明)")
    return gaps


def _ready_classification(tasks: list[dict], graph: dict,
                          versions: dict[str, str],
                          config_text: str) -> tuple[list[dict], list[dict]]:
    """把一份已取得的任务集合分为可开工与不可开工两侧(纯判断,不读取)。

    graph 由同一份任务集合生成;分流、进度、依赖、字段、版本漂移与能力
    规则按原语义保留。wontfix 与待执行之外的任务保留在 blocked 侧可见。
    """

    by_id = {task["identity"]: task for task in tasks}
    startable: list[dict] = []
    blocked: list[dict] = []
    for task in tasks:
        identity = task["identity"]
        reasons: list[str] = []
        triage = task["triage"]
        if triage == "needs-triage":
            reasons.append("分流:needs-triage(待核对当前目标后重新分流)")
        elif triage == "needs-info":
            missing = task["request"].get("尚缺信息", "")
            reasons.append(f"输入不足:needs-info(尚缺信息:{missing or '未列明'})")
        elif triage == "wontfix":
            reasons.append("分流:wontfix(不再安排;原因见任务记录)")
        if task["progress"] != "待执行":
            reasons.append(f"进度:{task['progress'] or '缺失'}(非待执行)")
        open_item = task["progress"] == "待执行" and triage != "wontfix"
        if open_item:
            for dep in graph["edges"].get(identity, []):
                if dep not in by_id:
                    reasons.append(f"依赖未解析:{dep}(任务不存在)")
                elif by_id[dep]["progress"] != "已完成":
                    reasons.append(
                        f"依赖未完成:{dep}(进度:{by_id[dep]['progress'] or '缺失'})")
            missing_fields = [key for key in PLAN_REQUEST_KEYS
                              if not task["request"].get(key)]
            if missing_fields:
                reasons.append(f"任务记录缺字段:{'、'.join(missing_fields)}")
            reasons.extend(_baseline_drifts(
                versions, task["request"].get("输入与基线", "")))
            reasons.extend(_capability_gaps(
                config_text, task["request"].get("所需能力", "")))
        entry = {"identity": identity, "title": task["title"], "triage": triage,
                 "progress": task["progress"],
                 "executor": task["request"].get("执行责任", ""),
                 "reasons": reasons}
        if (triage in ("ready-for-agent", "ready-for-human")
                and task["progress"] == "待执行" and not reasons):
            startable.append(entry)
        else:
            blocked.append(entry)
    return startable, blocked


def startable_tasks(project_root: Path | str,
                    config_rel: str = DEFAULT_CONFIG_REL, *,
                    transport=None, api_base: str | None = None,
                    cache_dir: Path | str | None = None) -> dict:
    """当前可开工集合:综合未完成依赖、输入、版本、能力与记录完整性。

    ready-for-agent 不等于依赖已完成或已获全部授权——见返回 note;
    wontfix 与非待执行任务保留在 blocked 侧可见,不静默消失。
    双后端同语义(任务来源经 CONFIG 分发;核心基线与执行条件仍读本地文档)。
    顶层携带任务读取元信息(cached/fetched_at/source,断网回缓存时另附
    cache_note)——缓存推断与当前确认可区分(审查修复票 01/S5)。
    """

    root = Path(project_root)
    reading = _read_workspace(root, config_rel, transport=transport,
                              api_base=api_base, cache_dir=cache_dir)
    # 基线版本表只读一次,供全部任务核对(避免逐任务重读核心文档)
    versions = _doc_baseline_versions(root, reading.config)
    # 依赖与任务状态都来自本次唯一的任务集合,不再回调公开依赖入口重取
    graph = _dependency_graph(reading.tasks)
    startable, blocked = _ready_classification(
        reading.tasks, graph, versions, reading.config_text)
    result = {"startable": startable, "blocked": blocked, "note": READY_NOTE}
    result.update(reading.fetch_meta)
    return result


# ---------- 基线内容指纹与受影响任务(任务票 15) ----------

# 基线登记两条指纹:内容指纹(空白敏感,任何变化都检出)与归一指纹(去空白,
# 只对字符增删敏感)。两者配合把「仅排版/空白差异」判为疑似格式修正,
# 字符增删判为实质变更(版本号未同步)。只有内容指纹时无法排除格式修正,
# 按未登记完整处理,不臆断。
_FINGERPRINT_RE = re.compile(r"内容指纹\s*[:：]\s*sha256:([0-9a-f]{64})")
_NORMALIZED_FP_RE = re.compile(r"归一指纹\s*[:：]\s*sha256:([0-9a-f]{64})")
# 规范化口径:全文中每处 sha256:<64 位十六进制> 都替换为固定占位再计算——
# 指纹行自身的取值因此不参与哈希(登记时可先写 64 个 0 再回填,规范化结果相同)。
_FP_SLOT_RE = re.compile(r"sha256:[0-9a-f]{64}")
BASELINE_NOTE = (
    "内容指纹用于发现手工修改或版本号未同步的情况;指纹变化先核对实际影响,"
    "疑似格式修正不自动触发需求重审、不作废既有成果与证据;"
    "实质变更需按实质影响处理(确认采纳则由该基线维护角色递增版本并更新指纹);"
    "受影响任务重新分流,原版本下完成事实保留,不自动算作满足新目标。")


def _canonical_fingerprint(text: str) -> str:
    """空白敏感指纹:sha256:<64hex> 槽位以占位替换后取 SHA-256。"""

    canonical = _FP_SLOT_RE.sub("sha256:<FP>", text)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalized_fingerprint(text: str) -> str:
    """空白归一指纹:槽位占位替换后去除全部空白再取 SHA-256。"""

    canonical = _FP_SLOT_RE.sub("sha256:<FP>", text)
    return hashlib.sha256("".join(canonical.split()).encode("utf-8")).hexdigest()


def baseline_report(project_root: Path | str,
                    config_rel: str = DEFAULT_CONFIG_REL, *,
                    transport=None, api_base: str | None = None,
                    cache_dir: Path | str | None = None) -> dict:
    """核对核心基线内容指纹并识别受影响任务(任务票 15)。

    - 每份核心基线(goal/design/tech 文档映射行):声明的基线版本、登记的
      内容指纹/归一指纹与当前值比对,报告 一致/指纹未登记/内容已变(疑似
      格式修正)/内容已变(实质变更)/文件缺失;仅空白差异判疑似格式修正,
      字符增删判实质变更(版本号未同步)。
    - 受影响任务:「输入与基线」引用了当前版本之外的核心基线(带版本号比对)
      的任务逐条列出;已完成/待验收条目附「保留原版本完成事实,不自动算作
      满足新目标」说明。
    - ok 仅在存在实质变更未同步时为 False;格式修正与版本引用过时不判 False
      (后者由 ready 逐任务报告)。
    """

    root = Path(project_root)
    config = load_config(root, config_rel)
    if config["backend"] not in SUPPORTED_BACKENDS:
        raise RecordsError(
            f"后端 {config['backend']} 未实现(首版支持 local-markdown 与 github-issues)")
    versions = _doc_baseline_versions(root, config)
    grouped = _core_rows(config["docmap"])
    docs: list[dict] = []
    seen_paths: set[str] = set()
    for key in ("goal", "design", "tech"):
        for row in grouped[key]:
            rel = row["path"]
            if rel in seen_paths:
                continue  # 重复映射位置只报一次(verify 另行判冲突)
            seen_paths.add(rel)
            path = root / rel
            if not path.is_file():
                docs.append({"path": rel, "content": row["content"],
                             "role": row["role"], "declared_version": None,
                             "recorded_fingerprint": None,
                             "current_fingerprint": None,
                             "status": "文件缺失",
                             "note": "核心基线权威位置不存在"})
                continue
            text = path.read_text(encoding="utf-8")
            version_match = re.search(r"基线版本\s*[:：]\s*v(\d+)", text)
            declared = f"v{version_match.group(1)}" if version_match else None
            strict_fp = _FINGERPRINT_RE.search(text)
            norm_fp = _NORMALIZED_FP_RE.search(text)
            current_strict = _canonical_fingerprint(text)
            current_norm = _normalized_fingerprint(text)
            if strict_fp is None or norm_fp is None:
                status, note = "指纹未登记", (
                    "该基线未完整登记内容指纹与归一指纹;由其维护角色在版本采纳"
                    "或格式修正同步时登记,登记后可检测版本号未同步的手工内容变更")
            elif strict_fp.group(1) == current_strict:
                status, note = "一致", "内容与登记指纹一致"
            elif norm_fp.group(1) == current_norm:
                status, note = "内容已变(疑似格式修正)", (
                    "仅空白/排版差异;不作废既有成果与证据,由维护角色在下一"
                    "次基线更新时同步指纹")
            else:
                status, note = "内容已变(实质变更)", (
                    "内容实质变化而版本号未同步;先核对实际影响,确认采纳由"
                    "维护角色递增版本并更新指纹,受影响任务重新分流")
            docs.append({"path": rel, "content": row["content"],
                         "role": row["role"], "declared_version": declared,
                         "recorded_fingerprint": (f"sha256:{strict_fp.group(1)}"
                                                  if strict_fp else None),
                         "current_fingerprint": f"sha256:{current_strict}",
                         "status": status, "note": note})

    reading = _read_workspace(root, config_rel, transport=transport,
                              api_base=api_base, cache_dir=cache_dir)
    affected: list[dict] = []
    tasks = reading.tasks
    for task in tasks:
        baseline_text = task["request"].get("输入与基线", "")
        for name, ref in _BASELINE_REF_RE.findall(baseline_text or ""):
            actual = versions.get(name) or versions.get(Path(name).stem)
            if not actual or actual == f"v{ref}":
                continue
            entry = {"identity": task["identity"], "title": task["title"],
                     "triage": task["triage"], "progress": task["progress"],
                     "doc": name, "ref_version": f"v{ref}",
                     "current_version": actual, "completion_fact": None}
            if task["progress"] in ("已完成", "待验收"):
                entry["completion_fact"] = (
                    f"保留原版本 v{ref} 下完成事实,不自动算作满足新目标"
                    f"({name} 当前 {actual})")
            affected.append(entry)
    return {"ok": all(d["status"] != "内容已变(实质变更)" for d in docs),
            "docs": docs, "affected_tasks": affected, "note": BASELINE_NOTE}


# ---------- 两后端共享的核心校验(定义在 mgs_record_model) ----------
# 同一份规范化任务(本地 work/task.md 与 GitHub Issue 正文是同一记录格式)
# 在两后端必须得到相同核验结论:标签映射、核心文档映射、任务核心字段
# (身份形态、五类分流、进度、工作请求必填字段)与依赖关系在 mgs_record_model
# 单一实现;各后端只保留存储特有检查(本地:目录一致性、结果文件与索引;
# GitHub:远端标签实际存在、评论一致性、标签与正文冲突、关闭原因、身份重复)。





def verify_project(project_root: Path | str,
                   config_rel: str = DEFAULT_CONFIG_REL, *,
                   transport=None, api_base: str | None = None,
                   cache_dir: Path | str | None = None) -> dict:
    """回读核验:后端、五标签完整且不冲突、核心文档唯一权威位置、任务结构。

    github-issues 后端(任务票 17)的远端侧检查由 mgs_github 承担:
    仓库坐标明确、映射标签在仓库实际存在、远端任务结构有效、依赖可解析
    无循环、评论结果与所属任务一致;离线时远端侧检查标注「未核对」,
    不冒充已核验。
    """

    root = Path(project_root)
    checks: list[dict] = []
    try:
        config = load_config(root, config_rel)
    except RecordsError as exc:
        return {"ok": False, "checks": [check_item("config-present", False, str(exc))]}
    checks.append(check_item("config-present", True, str(root / config_rel)))
    if config["backend"] == "github-issues":
        return github_backend(root, config_rel, transport=transport,
                              api_base=api_base, cache_dir=cache_dir).verify(root)
    if config["backend"] != "local-markdown":
        checks.append(check_item("backend-local-markdown", False,
                             f"backend={config['backend']} 未实现"))
        return {"ok": False, "checks": checks}
    checks.append(check_item("backend-local-markdown", True,
                         f"backend={config['backend']}"))
    task_root = _task_root(root, config)
    checks.append(check_item("task-root-exists", task_root.is_dir(),
                         str(task_root)))

    # 标签映射与核心文档映射:两后端共享的单一实现(审查修复票 01/核验建议 1)
    checks += label_mapping_checks(config["labels"])
    checks += docmap_checks(root, config["docmap"])

    tasks = list_tasks(root, config_rel)
    task_problems: list[str] = []
    for task in tasks:
        if task["identity"] != task["directory"]:
            task_problems.append(f"{task['directory']}:身份 {task['identity']!r} 与目录不一致")
        # 任务核心字段:两后端共享的单一实现(含工作请求必填字段)
        task_problems += task_core_problems(task, task["directory"])
    checks.append(check_item("tasks-valid", not task_problems,
                         ";".join(task_problems) if task_problems
                         else f"{len(tasks)} 个任务结构有效"))

    result_problems: list[str] = []
    for task in tasks:
        task_dir = task_root / task["directory"]
        for rel in task["results"]:
            result_path = task_dir / rel
            text = result_path.read_text(encoding="utf-8")
            if task["identity"] not in text:
                result_problems.append(f"{task['directory']}/{rel}:未引用所属任务身份")
        if task["results"]:
            index_text = task["result_index_text"].strip()
            referenced = any(name.split("/")[-1] in index_text or "results" in index_text
                             for name in task["results"])
            if not referenced or "(暂无)" in index_text:
                result_problems.append(
                    f"{task['directory']}:结果文件存在但结果索引未引用")
    checks.append(check_item("results-consistent", not result_problems,
                         ";".join(result_problems) if result_problems
                         else "结果文件与结果索引互相一致"))

    # 依赖关系可解析且无循环(两后端共享;旧记录无「依赖」字段时视为无依赖)
    dep_problems = dependency_problems(tasks)
    checks.append(check_item("deps-consistent", not dep_problems,
                         ";".join(dep_problems) if dep_problems
                         else "依赖关系可解析且无循环"))
    return {"ok": all(item["ok"] for item in checks), "checks": checks}


# ---------- CLI ----------

def _parse_fields(pairs: list[str]) -> dict:
    fields: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise RecordsError(f"字段必须形如 键=值,当前 {pair!r}")
        key, value = pair.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def _cli() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", required=True, help="目标项目根目录")
    common.add_argument("--config", default=DEFAULT_CONFIG_REL,
                        help=f"CONFIG 相对路径(默认 {DEFAULT_CONFIG_REL})")
    common.add_argument("--api-base", default=None,
                        help="GitHub API 端点覆盖(测试/本地替身;默认按 host 推导,"
                             "或环境变量 MGS_GH_API_BASE)")
    common.add_argument("--cache-dir", default=None,
                        help="远端读取缓存与未发布草稿目录(离线缓存/草稿语义)")
    parser = argparse.ArgumentParser(
        description="任务后端统一接口(本地 Markdown 读取与核验;"
                    "github-issues 后端读写与切换迁移)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("config", parents=[common], help="读取协作配置")
    sub.add_parser("list", parents=[common], help="列出任务")
    p_show = sub.add_parser("show", parents=[common], help="读取单个任务")
    p_show.add_argument("--task", required=True, help="任务身份")
    sub.add_parser("deps", parents=[common],
                   help="解析任务依赖关系(未解析引用或循环时退出码 1)")
    sub.add_parser("ready", parents=[common], help="当前可开工集合及原因")
    sub.add_parser("baseline", parents=[common],
                   help="核心基线内容指纹核对与受影响任务"
                        "(存在实质变更未同步时退出码 1)")
    sub.add_parser("verify", parents=[common], help="回读核验")
    # github-issues 后端写操作(任务票 17;本地后端写入经 mgs-gate 受控通道)
    p_create = sub.add_parser(
        "create", parents=[common], help="创建远端任务(防重复:同身份收养)")
    p_create.add_argument("--identity", required=True, help="任务身份(NN-<slug>)")
    p_create.add_argument("--title", required=True, help="任务标题")
    p_create.add_argument("--field", action="append", default=[],
                          help="工作请求字段 键=值,可重复")
    p_create.add_argument("--triage", default="needs-triage",
                          choices=CANONICAL_LABELS, help="初始分流")
    p_create.add_argument("--progress", default="待执行", help="初始进度")
    p_update = sub.add_parser(
        "update", parents=[common], help="更新任务安排(字段合并,可带版本校验)")
    p_update.add_argument("--task", required=True, help="任务身份")
    p_update.add_argument("--field", action="append", default=[],
                          help="字段 键=值(进度/工作请求字段),可重复")
    p_update.add_argument("--change-note", default=None,
                          help="安排更新说明(写入状态变化;缺省「安排更新」;"
                               "与草稿保存/重放共用同一参数)")
    p_update.add_argument("--expected-body-sha256", default=None,
                          help="预期远端正文 SHA-256(不符则拒绝,不覆盖他人改动)")
    p_append = sub.add_parser(
        "append-result", parents=[common], help="追加结果评论并登记结果索引")
    p_append.add_argument("--task", required=True, help="任务身份")
    src = p_append.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="结果正文(Markdown)")
    src.add_argument("--file", help="结果正文文件路径")
    p_triage = sub.add_parser(
        "set-triage", parents=[common], help="设置分流(标签与正文同步)")
    p_triage.add_argument("--task", required=True, help="任务身份")
    p_triage.add_argument("--label", required=True, choices=CANONICAL_LABELS)
    p_rels = sub.add_parser(
        "set-relations", parents=[common], help="设置依赖(明确可解析引用)")
    p_rels.add_argument("--task", required=True, help="任务身份")
    p_rels.add_argument("--dep", action="append", default=[],
                        help="依赖任务身份,可重复;留空表示无依赖")
    p_parent = sub.add_parser(
        "set-parent", parents=[common],
        help="设置父任务(优先原生 sub-issues,不可用回退正文引用)")
    p_parent.add_argument("--task", required=True, help="任务身份")
    p_parent.add_argument("--parent", default=None, help="父任务身份;省略即解除")
    p_close = sub.add_parser(
        "close", parents=[common],
        help="关闭任务(完成/不再执行/已有成果覆盖;关闭不等于验收通过)")
    p_close.add_argument("--task", required=True, help="任务身份")
    p_close.add_argument("--reason", required=True,
                         choices=["完成", "不再执行", "已有成果覆盖"])
    p_close.add_argument("--note", default="", help="关闭说明(入评论)")
    sub.add_parser("publish-drafts", parents=[common],
                   help="重放未发布草稿(远端恢复后)")
    p_handover = sub.add_parser(
        "handover", parents=[common],
        help="远端交接核对基线引用可达(未发布本地资料不宣称远端可访问;"
             "不可达时退出码 1)")
    p_plan = sub.add_parser(
        "switch-plan", parents=[common],
        help="生成后端切换迁移清单(只读;确认前不执行)")
    p_plan.add_argument("--target", required=True,
                        choices=["github-issues", "local-markdown"])
    p_plan.add_argument("--repo", default=None,
                        help="目标为 github-issues 时的 host/owner/repository")
    p_plan.add_argument("--emit", default=None, help="迁移清单 JSON 输出路径")
    p_apply = sub.add_parser(
        "switch-apply", parents=[common],
        help="执行已确认的切换(目标侧创建+产出新 CONFIG;不改写项目 CONFIG)")
    p_apply.add_argument("--plan", required=True, help="switch-plan 产出的清单")
    p_apply.add_argument("--emit-dir", required=True, help="产出目录")
    p_apply.add_argument("--confirmed", action="store_true",
                         help="确认标记(未确认则拒绝执行)")

    args = parser.parse_args()
    root = Path(args.project)
    remote = {"transport": None, "api_base": args.api_base,
              "cache_dir": args.cache_dir}

    def read_transport(config: dict):
        """CLI 子命令所需的真实读取通道(审查修复票 01/S3、S4):反向
        switch-plan 要读取 github 源任务,handover 要实际执行可达检查;
        --api-base/环境变量可指向本地替身,不注入测试桩。"""

        import mgs_github  # noqa: PLC0415

        return mgs_github.UrllibTransport(
            api_base=mgs_github.api_base_for(config, args.api_base),
            token=mgs_github.token_from_env())

    def github_only(action: str):
        import mgs_github  # noqa: PLC0415

        config = load_config(root, args.config)
        if config["backend"] != "github-issues":
            raise RecordsError(
                f"{action} 仅支持 github-issues 后端(当前 {config['backend']});"
                "本地 Markdown 后端的项目内写入一律经 mgs-gate 受控通道"
                "(mgs_write),本 CLI 不提供绕过")
        return mgs_github.GithubBackend(
            config, read_transport(config), args.cache_dir)

    try:
        if args.cmd == "config":
            payload: object = load_config(root, args.config)
        elif args.cmd == "list":
            payload = [{"identity": t["identity"], "title": t["title"],
                        "triage": t["triage"], "progress": t["progress"],
                        **({"cached_read": True} if t.get("cached_read") else {})}
                       for t in list_tasks(root, args.config, **remote)]
        elif args.cmd == "show":
            payload = read_task(root, args.task, args.config, **remote)
        elif args.cmd == "deps":
            payload = task_dependencies(root, args.config, **remote)
        elif args.cmd == "ready":
            payload = startable_tasks(root, args.config, **remote)
        elif args.cmd == "baseline":
            payload = baseline_report(root, args.config, **remote)
        elif args.cmd == "verify":
            payload = verify_project(root, args.config, **remote)
        elif args.cmd == "create":
            payload = github_only("create").create_task(
                args.identity, args.title, _parse_fields(args.field),
                triage=args.triage, progress=args.progress)
        elif args.cmd == "update":
            if not args.field:
                raise RecordsError("update 至少需要一个 --field")
            payload = github_only("update").update_task(
                args.task, _parse_fields(args.field),
                expected_body_sha256=args.expected_body_sha256,
                change_note=args.change_note or "安排更新")
        elif args.cmd == "append-result":
            text = (Path(args.file).read_text(encoding="utf-8") if args.file
                    else args.text)
            payload = github_only("append-result").append_result(args.task, text)
        elif args.cmd == "set-triage":
            payload = github_only("set-triage").set_triage(args.task, args.label)
        elif args.cmd == "set-relations":
            payload = github_only("set-relations").set_relations(
                args.task, args.dep)
        elif args.cmd == "set-parent":
            payload = github_only("set-parent").set_parent(args.task, args.parent)
        elif args.cmd == "close":
            payload = github_only("close").close_task(
                args.task, args.reason, note=args.note)
        elif args.cmd == "publish-drafts":
            payload = github_only("publish-drafts").publish_drafts()
        elif args.cmd == "handover":
            import mgs_github  # noqa: PLC0415

            config = load_config(root, args.config)
            if config["backend"] != "github-issues":
                raise RecordsError(
                    f"handover 仅用于 github-issues 后端的远端交接核对"
                    f"(当前 {config['backend']})")
            # 可达性结论只能来自实际执行的检查(S4):建立真实读取通道
            payload = mgs_github.handover_baseline_check(
                root, args.config, transport=read_transport(config))
        elif args.cmd == "switch-plan":
            import mgs_github  # noqa: PLC0415

            config = load_config(root, args.config)
            payload = mgs_github.plan_backend_switch(
                root, target=args.target, repo=args.repo,
                transport=read_transport(config), cache_dir=args.cache_dir)
            if args.emit:
                Path(args.emit).write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8")
        elif args.cmd == "switch-apply":
            import mgs_github  # noqa: PLC0415

            plan_data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            transport = None
            if plan_data.get("to") == "github-issues":
                host = mgs_github.parse_repo_location(plan_data["repo"])["host"]
                base = (args.api_base
                        or os.environ.get(mgs_github.API_BASE_ENV, "").strip()
                        or mgs_github.default_api_base(host))
                transport = mgs_github.UrllibTransport(
                    base, mgs_github.token_from_env())
            payload = mgs_github.apply_backend_switch(
                args.plan, confirmed=args.confirmed, emit_dir=args.emit_dir,
                project_root=root, transport=transport,
                cache_dir=args.cache_dir)
        else:  # pragma: no cover - 子命令已穷举
            raise RecordsError(f"未知子命令 {args.cmd}")
    except RecordsError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    except OSError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    if args.cmd == "verify" and not payload["ok"]:
        return 1
    if args.cmd == "deps" and not payload["ok"]:
        return 1
    if args.cmd == "baseline" and not payload["ok"]:
        return 1
    if args.cmd == "handover" and not payload["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
