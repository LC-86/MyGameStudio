#!/usr/bin/env python3
"""MyGameStudio 本地 Markdown 任务后端:统一回读与本地写入接口(任务票 04,票 08/15 扩展,
票 17 增加对 github-issues 后端的分发与写操作 CLI;issue #51 补齐本地写入、
接入与只读状态查询,普通本地工作不经 mgs-gate)。

对应设计《工作记录合同》「后端接口」一节:读取配置、列出任务、读取任务与结果、
回读核验(票 04);关系解析与循环检测、当前可开工集合(票 08);核心基线内容
指纹核对与受影响任务识别(票 15);GitHub Issues 后端同语义适配与切换迁移
(票 17,适配器在 mgs_github.py)。调用方只使用 CONFIG.md 配置后的入口,
不硬编码 work/ 或 .scratch/(配置路径可显式传入,默认值来自
《项目目录模板》的默认布局)。

边界:
- 本地 Markdown 后端:读取、核验与写入(创建/更新/认领/关闭/结果)均经本接口;
  普通本地工作不经 mgs-gate。核验针对实际落盘内容。
- GitHub Issues 后端(任务票 17):读取经 mgs_github 传输层(远端不可用回
  注明时间与来源的缓存,不静默切本地);远端写操作先核对 CONFIG 中明确到仓库
  的 issues-write 授权。GitHub 原生接入的完整项目路径由后续票扩充。
- 未实现的其他后端:明确报不支持,不静默降级。
- 开工集合是「记录可核对的开工条件」判断,不是授权:ready-for-agent
  不等于依赖已完成或已获全部写入授权,开工前仍需按任务允许修改范围与
  运行保障核对授权(startable_tasks 输出附此提示)。
- 命令行层(参数解析、输出投影与退出码)定义在 mgs_records_cli.py
  (PR #28 复审 ST-1:查询组织与命令行职责分离);本文件保持旧脚本
  原调用入口,子命令、参数、JSON 输出与退出码合同不变。

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

import datetime as _dt
import hashlib
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


def _read_tasks(root: Path, config: dict, *, transport=None,
                api_base: str | None = None,
                cache_dir: Path | str | None = None) -> tuple[list[dict], dict]:
    """由本次已加载配置获取任务集合一次(不重读 CONFIG)。

    本地每份 task.md 读取一次并保持目录顺序;GitHub 全量任务集合获取一次
    并保留原后端顺序。依赖与可开工判断都从这一份结果推导,调用方在同一
    份集合上复用,不再回调重新获取任务的公开入口。读取元信息(是否缓存、
    抓取时间与来源)随结果返回——离线回缓存与在线当前确认由此可区分
    (审查修复票 01/S5)。
    """

    backend = config["backend"]
    if backend == "local-markdown":
        tasks = local_list_tasks(root, config)
        fetch_meta = {
            "cached": False,
            "fetched_at": _dt.datetime.now().astimezone().isoformat(
                timespec="seconds"),
            "source": {"backend": "local-markdown",
                       "task_root": config["task_root"]}}
        return tasks, fetch_meta
    if backend == "github-issues":
        payload = _github_backend_for(
            config, transport=transport, api_base=api_base,
            cache_dir=cache_dir).fetch_tasks()
        fetch_meta = {"cached": bool(payload.get("cached")),
                      "fetched_at": payload.get("fetched_at"),
                      "source": payload.get("source")}
        if fetch_meta["cached"]:
            fetch_meta["cache_note"] = payload.get("note", "")
        return payload["tasks"], fetch_meta
    raise RecordsError(
        f"后端 {backend} 未实现(首版支持 local-markdown 与 github-issues)")


def _read_workspace(project_root: Path | str, config_rel: str, *,
                    transport=None, api_base: str | None = None,
                    cache_dir: Path | str | None = None) -> _Reading:
    """顶层读取一次:CONFIG 原文一次;需要任务集合时获取一次。

    任务集合保留来源顺序,本次判断都从这一份结果推导;下一次顶层调用重新
    读取,不复用本次载体。
    """

    root = Path(project_root)
    config, config_text = load_config_document(root, config_rel)
    tasks, fetch_meta = _read_tasks(root, config, transport=transport,
                                    api_base=api_base, cache_dir=cache_dir)
    return _Reading(config, config_text, tasks, fetch_meta)


def list_tasks(project_root: Path | str, config_rel: str = DEFAULT_CONFIG_REL,
               *, transport=None, api_base: str | None = None,
               cache_dir: Path | str | None = None) -> list[dict]:
    """列出任务身份、标题、分流与进度(经 CONFIG 解析任务源,不硬编码)。

    github-issues 后端经远端适配器列出(离线时返回任务级 cached_read 标注);
    本地后端委托 mgs_record_source 的本地 adapter,按目录顺序列举。本次调用
    只读一次 CONFIG,并直接以该配置构造对应后端(不再按相对路径二次读取)。
    """

    root = Path(project_root)
    config = load_config(root, config_rel)
    if config["backend"] == "github-issues":
        payload = _github_backend_for(
            config, transport=transport, api_base=api_base,
            cache_dir=cache_dir).fetch_tasks()
        cached = bool(payload.get("cached"))
        # 排序与离线标记使用独立投影:不原地修改后端返回的任务集合,避免
        # 调用特有标注影响其他判断(list 按身份排序,来源集合保持原顺序)。
        return [dict(task, cached_read=True) if cached else dict(task)
                for task in sorted(payload["tasks"],
                                   key=lambda task: task["identity"])]
    if config["backend"] != "local-markdown":
        raise RecordsError(
            f"后端 {config['backend']} 未实现(首版支持 local-markdown 与 github-issues)")
    return local_list_tasks(root, config)


def read_task(project_root: Path | str, task_id: str,
              config_rel: str = DEFAULT_CONFIG_REL, *, transport=None,
              api_base: str | None = None,
              cache_dir: Path | str | None = None) -> dict:
    """读取单个任务:头部字段、请求、小节与结果清单。

    本次调用只读一次 CONFIG(本地 show 按目录定位,不扫描无关任务);
    GitHub show 由已加载配置直接构造后端,内部仍按接口需要读取集合定位、
    Issue 详情与评论——不为减少请求删掉必要读取。
    """

    root = Path(project_root)
    config = load_config(root, config_rel)
    if config["backend"] == "github-issues":
        return _github_backend_for(
            config, transport=transport, api_base=api_base,
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


def _doc_texts(root: Path, config: dict, *,
               config_text: str | None = None) -> dict[str, str]:
    """读取文档映射中实际存在文件的原文一次(路径→原文,供本次调用复用)。

    同一已读原文同时用于逻辑版本与内容指纹判断;下一次顶层调用重新读取,
    不做跨调用缓存(第一阶段设计:核心文档按实际路径复用已读文本)。
    复用键是**解析后的实际路径**(spec 10):同一物理文件经 docs/DESIGN.md 与
    docs/./DESIGN.md 等合法映射写法出现时只实际读取一次,各映射路径仍分别
    定位输出,不因写法差异混入两次读取结果(PR #28 复审 SP-2)。
    ``config_text`` 是本次顶层调用已取得的 CONFIG 原文(spec 9:每次顶层调用
    取得 CONFIG 原文一次,由同一原文解析配置与执行条件):文档映射含 CONFIG
    自映射时复用该原文,不二次读取(PR #28 二轮审查 R2-SP-1)。
    """

    texts: dict[str, str] = {}
    by_location: dict[str, str] = {}  # 解析后实际路径 → 本次已读原文
    if config_text is not None:
        by_location[str((root / config["config_path"]).resolve())] = config_text
    for row in config["docmap"]:
        rel = row["path"]
        if rel in texts:
            continue
        path = root / rel
        if not path.is_file():
            continue
        location = str(path.resolve())
        text = by_location.get(location)
        if text is None:
            text = path.read_text(encoding="utf-8")
            by_location[location] = text
        texts[rel] = text
    return texts


def _versions_from_texts(config: dict, texts: dict[str, str]) -> dict[str, str]:
    """由同一份已读文档原文建立逻辑版本表(如 GAME_DESIGN → "v2")。"""

    versions: dict[str, str] = {}
    for row in config["docmap"]:
        text = texts.get(row["path"])
        if text is None:
            continue
        match = re.search(r"基线版本\s*[:：]\s*v(\d+)", text)
        if match:
            value = f"v{match.group(1)}"
            versions[row["path"]] = value
            stem = Path(row["path"]).stem
            versions.setdefault(stem, value)
            versions.setdefault(str(Path(row["path"]).name), value)
    return versions


def _doc_baseline_versions(root: Path, config: dict, *,
                           config_text: str | None = None) -> dict[str, str]:
    """按文档映射建立可引用文档的当前逻辑版本表(如 GAME_DESIGN → "v2")。

    ``config_text`` 透传给 ``_doc_texts``:CONFIG 自映射时复用顶层已读原文;
    keyword-only 与 ``_doc_texts`` 一致,省略即显式声明无顶层原文可复用。
    """

    return _versions_from_texts(
        config, _doc_texts(root, config, config_text=config_text))


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
    # 基线版本表只读一次,供全部任务核对(避免逐任务重读核心文档);
    # CONFIG 自映射行复用 _read_workspace 已读原文,不二次读取
    versions = _doc_baseline_versions(
        root, reading.config, config_text=reading.config_text)
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
    # 本次判断只用同一份 CONFIG 原文与已读核心文档:一次读取、版本与指纹同源
    # (config_text 复用给文档映射的 CONFIG 自映射行,R2-SP-1)
    config, config_text = load_config_document(root, config_rel)
    if config["backend"] not in SUPPORTED_BACKENDS:
        raise RecordsError(
            f"后端 {config['backend']} 未实现(首版支持 local-markdown 与 github-issues)")
    texts = _doc_texts(root, config, config_text=config_text)
    versions = _versions_from_texts(config, texts)
    grouped = _core_rows(config["docmap"])
    docs: list[dict] = []
    seen_paths: set[str] = set()
    for key in ("goal", "design", "tech"):
        for row in grouped[key]:
            rel = row["path"]
            if rel in seen_paths:
                continue  # 重复映射位置只报一次(verify 另行判冲突)
            seen_paths.add(rel)
            text = texts.get(rel)
            if text is None:
                docs.append({"path": rel, "content": row["content"],
                             "role": row["role"], "declared_version": None,
                             "recorded_fingerprint": None,
                             "current_fingerprint": None,
                             "status": "文件缺失",
                             "note": "核心基线权威位置不存在"})
                continue
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

    # 任务集合同样由本次已加载配置获取一次(不重读 CONFIG),受本次同调用约束
    tasks, _ = _read_tasks(root, config, transport=transport,
                           api_base=api_base, cache_dir=cache_dir)
    affected: list[dict] = []
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
    不冒充已核验。标签、评论与本地结果文件的核验读取照常实际发生
    (一次任务集合获取不等于只允许一个网络请求)。

    本次调用只读一次 CONFIG 并直接以该配置构造后端;本地任务集合由该配置
    获取一次,不再按相对路径二次读取。
    """

    root = Path(project_root)
    checks: list[dict] = []
    try:
        config = load_config(root, config_rel)
    except RecordsError as exc:
        return {"ok": False, "checks": [check_item("config-present", False, str(exc))]}
    checks.append(check_item("config-present", True, str(root / config_rel)))
    if config["backend"] == "github-issues":
        # 由本次已解析配置构造后端(verify 内部自行完成任务集合、标签与评论读取)
        return _github_backend_for(
            config, transport=transport, api_base=api_base,
            cache_dir=cache_dir).verify(root)
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

    # 任务集合由本次已加载配置获取一次(不重读 CONFIG);畸形任务不被过滤
    tasks, _ = _read_tasks(root, config)
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


# ---------- 本地接入、任务写入与只读状态(issue #51) ----------

def analyze_project(project_root: Path | str) -> dict:
    """Game-Init 只读分析:不写入,也不开始制作。"""

    import mgs_onboard  # noqa: PLC0415

    return mgs_onboard.analyze_project(project_root)


def plan_local_onboarding(project_root: Path | str) -> dict:
    """选择本地 Markdown 为唯一现行 tracker,形成接入清单(不写入)。"""

    import mgs_onboard  # noqa: PLC0415

    return mgs_onboard.plan_local_onboarding(project_root)


def apply_local_onboarding(project_root: Path | str, plan: dict | None = None,
                           *, confirmed: bool = False) -> dict:
    """按确认清单接入;不覆盖有效旧资料,普通路径不依赖 gate。"""

    import mgs_onboard  # noqa: PLC0415

    return mgs_onboard.apply_local_onboarding(
        project_root, plan, confirmed=confirmed)


def _backend_for(project_root: Path | str, config_rel: str = DEFAULT_CONFIG_REL,
                 *, transport=None, api_base: str | None = None,
                 cache_dir: Path | str | None = None):
    """按现行 CONFIG 构造可写后端(本地不经 gate;GitHub 仍走既有授权)。"""

    config = load_config(project_root, config_rel)
    if config["backend"] == "local-markdown":
        import mgs_local_backend  # noqa: PLC0415

        return mgs_local_backend.LocalMarkdownBackend(project_root, config)
    if config["backend"] == "github-issues":
        return _github_backend_for(
            config, transport=transport, api_base=api_base, cache_dir=cache_dir)
    raise RecordsError(
        f"后端 {config['backend']} 未实现(首版支持 local-markdown 与 github-issues)")


def create_task(project_root: Path | str, identity: str, title: str,
                request: dict, *, triage: str = "needs-triage",
                progress: str = "待执行",
                config_rel: str = DEFAULT_CONFIG_REL, transport=None,
                api_base: str | None = None,
                cache_dir: Path | str | None = None) -> dict:
    """记录一项任务。本地 Markdown 先回读再创建,已存在则收养。"""

    return _backend_for(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir).create_task(
            identity, title, request, triage=triage, progress=progress)


def update_task(project_root: Path | str, identity: str, fields: dict, *,
                expected_body_sha256: str | None = None,
                change_note: str = "安排更新",
                config_rel: str = DEFAULT_CONFIG_REL, transport=None,
                api_base: str | None = None,
                cache_dir: Path | str | None = None) -> dict:
    """更新任务安排。expected_body_sha256 不符则保留双方成果并拒绝覆盖。"""

    return _backend_for(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir).update_task(
            identity, fields, expected_body_sha256=expected_body_sha256,
            change_note=change_note)


def set_triage(project_root: Path | str, identity: str, label: str, *,
               config_rel: str = DEFAULT_CONFIG_REL, transport=None,
               api_base: str | None = None,
               cache_dir: Path | str | None = None) -> dict:
    return _backend_for(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir).set_triage(identity, label)


def set_relations(project_root: Path | str, identity: str, deps: list[str], *,
                  config_rel: str = DEFAULT_CONFIG_REL, transport=None,
                  api_base: str | None = None,
                  cache_dir: Path | str | None = None) -> dict:
    return _backend_for(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir).set_relations(identity, deps)


def set_parent(project_root: Path | str, identity: str, parent_id: str | None,
               *, config_rel: str = DEFAULT_CONFIG_REL, transport=None,
               api_base: str | None = None,
               cache_dir: Path | str | None = None) -> dict:
    return _backend_for(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir).set_parent(identity, parent_id)


def claim_task(project_root: Path | str, identity: str, actor: str, *,
               config_rel: str = DEFAULT_CONFIG_REL, transport=None,
               api_base: str | None = None,
               cache_dir: Path | str | None = None) -> dict:
    backend = _backend_for(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir)
    if not hasattr(backend, "claim_task"):
        raise RecordsError("当前后端本票不提供认领写接缝(GitHub 接入见后续票)")
    return backend.claim_task(identity, actor)


def append_result(project_root: Path | str, identity: str, result_markdown: str,
                  *, config_rel: str = DEFAULT_CONFIG_REL, transport=None,
                  api_base: str | None = None,
                  cache_dir: Path | str | None = None) -> dict:
    return _backend_for(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir).append_result(identity, result_markdown)


def close_task(project_root: Path | str, identity: str, reason: str,
               note: str = "", *, config_rel: str = DEFAULT_CONFIG_REL,
               transport=None, api_base: str | None = None,
               cache_dir: Path | str | None = None) -> dict:
    return _backend_for(
        project_root, config_rel, transport=transport, api_base=api_base,
        cache_dir=cache_dir).close_task(identity, reason, note=note)


def cancel_operation(project_root: Path | str, op: str, identity: str, *,
                     note: str = "", config_rel: str = DEFAULT_CONFIG_REL) -> dict:
    """登记已撤销动作;恢复时不得重放。"""

    import mgs_local_backend  # noqa: PLC0415

    config = load_config(project_root, config_rel)
    if config["backend"] != "local-markdown":
        raise RecordsError("本票只登记本地 Markdown 的撤销,不提前做 GitHub 接入")
    return mgs_local_backend.LocalMarkdownBackend(
        project_root, config).cancel_operation(op, identity, note=note)


def status_report(project_root: Path | str,
                  config_rel: str = DEFAULT_CONFIG_REL, *,
                  transport=None, api_base: str | None = None,
                  cache_dir: Path | str | None = None) -> dict:
    """Game-Producer 只读状态:真实记录中的目标、进度、缺口和下一步。"""

    root = Path(project_root)
    config = load_config(root, config_rel)
    tasks = list_tasks(root, config_rel, transport=transport,
                       api_base=api_base, cache_dir=cache_dir)
    ready = startable_tasks(root, config_rel, transport=transport,
                            api_base=api_base, cache_dir=cache_dir)
    gaps: list[str] = []
    for row in config.get("docmap", []):
        rel = row.get("path") or ""
        if rel and not (root / rel).is_file():
            gaps.append(f"缺项:{row.get('content')} → {rel}")
    if not tasks:
        gaps.append("缺项:尚无任务记录")
    startable = ready.get("startable") or []
    if startable:
        first = startable[0]
        next_step = (f"可开工 {first.get('identity')} {first.get('title')} "
                     f"(分流 {first.get('triage')};可开工不等于已获授权)")
    elif tasks:
        next_step = "无记录层面可开工任务;见缺口与 blocked 原因"
    else:
        next_step = "尚未记录任务"
    goals = ""
    project_path = root / "docs/mygamestudio/PROJECT.md"
    if project_path.is_file():
        goals = project_path.read_text(encoding="utf-8")[:400]
    return {
        "wrote": False,
        "backend": config["backend"],
        "goals": goals,
        "tasks": tasks,
        "gaps": gaps,
        "missing": gaps,
        "startable": startable,
        "blocked": ready.get("blocked") or [],
        "next": next_step,
        "note": ready.get("note", READY_NOTE),
    }


# ---------- 兼容入口 ----------

# 命令行层(参数解析、输出投影、退出码)唯一定义在 mgs_records_cli;本文件
# 保持旧脚本原调用入口与退出码合同(PR #28 复审 ST-1)。脚本实例即本模块
# 本体:先注册再导入 CLI 层,查询组织不会被重复执行,也不会反向成为
# mgs_records_cli 的模块级依赖环。
if __name__ == "__main__":
    sys.modules.setdefault("mgs_records", sys.modules[__name__])
    from mgs_records_cli import _cli  # noqa: E402  (脚本入口延迟导入)
    sys.exit(_cli())
