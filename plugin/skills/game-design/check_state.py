#!/usr/bin/env python3
"""Game-Design 检查时机与复用的状态基元与判定规则(统一设计问答框架票 08)。

公开 interface:
  snapshot(state) -> dict
  public(value) -> Any
  log(state, entry) -> None
  count(state, op, paths, call) -> None
  count_of(events, op) -> dict
  fingerprint(value) -> str
  baseline_changed(path, fingerprint, state) -> bool
  in_scope(state, item) -> bool
  scope_paths(state) -> list[str]
  scope_path_keys(state) -> list[str]
  result_affected(result, affected) -> bool
  target_paths(target) -> list[str]
  within(path, pattern) -> bool
  references(text) -> list[str]
  adoption_gaps(answers, adopted) -> list[str]
  contradictions(adopted, history) -> list[str]
  entry_failures(recorded, parsed, entries, pending) -> list[str]
  reference_failures(text, state, module, known_paths) -> list[str]
  forget_target(state, target) -> list[str]
  impact_items(plan) -> list[Any]
  paths(files) -> list[str]

``checks.py`` 的检查时机入口共用这些基元:会话状态以内容身份(路径 + SHA-256
指纹)与适用范围为准,判定规则只依赖调用方给出的结构化输入,不读文件、不写入、
不接触受控通道。``INVALIDATION`` 与 ``GLOBAL_SCOPE`` 等常量是检查台账与报告
共用的措辞与范围标签,避免各流程各写一套。
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

from decision_records import SYNC_PENDING, parse_record, sha256_text

GLOBAL_SCOPE = "全局"
CONVERGE_SCOPE = "收敛统一核对"
SKIPPED_GLOBAL_CHECK = "全局重查（全项目基线、全部链接、远端任务）"

INVALIDATION = {
    "external_change": "外部修改了引用目标",
    "revoked_authorization": "授权被撤销",
    "version_conflict": "版本冲突",
    "write_failed": "写入失败",
    "broken_link": "断链",
    "insufficient_evidence": "证据不足",
}

ANSWER_SOURCES = {"user", "recommendation", "custom", "revision"}
OVERALL_RE = re.compile(r"整体按建议|全部按建议|都按建议")
REJECT_OVERALL_RE = re.compile(
    r"(不要|别|先不).{0,10}(整体|全部|都)?按建议")
CHOICE_RE = re.compile(r"(Q\d+)\s*选\s*([A-Za-z])")
ADJUST_RE = re.compile(
    r"(Q\d+)\s*(?:调整为|改为|：|:)\s*(.+?)(?:[，。；\n]|$)")
UNKNOWN_VALUE_RE = re.compile(r"不知道|不清楚|先不确定")


def snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """浅拷贝会话,使每个入口都返回新状态(不共享可变容器)。"""

    updated = dict(state or {})
    for key in ("reads",):
        updated[key] = {name: dict(item)
                        for name, item in (updated.get(key) or {}).items()}
    for key in ("results", "evidence", "ledger", "round_checks"):
        updated[key] = [dict(item) for item in (updated.get(key) or [])]
    return updated


def public(value: Any) -> Any:
    """内部状态可含集合;对外一律转为稳定、可核对的形态。"""

    if isinstance(value, dict):
        return {str(key): public(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [public(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def log(state: dict[str, Any], entry: dict[str, Any]) -> None:
    """登记一条检查台账:时机、范围、结果与明细,跳过项如实保留。"""

    state.setdefault("ledger", []).append(
        {key: public(value) for key, value in entry.items()
         if value is not None})


def count(state: dict[str, Any], op: str, paths: Iterable[str],
          call: str) -> None:
    """登记一次实际读取或写入:一条调用内的多个文件各自计入。"""

    state.setdefault("evidence", []).append(
        {"op": str(op), "paths": [str(item) for item in paths],
         "call": str(call)})


def count_of(events: list[dict[str, Any]], op: str) -> dict[str, Any]:
    """按事件计数:``file_ops`` 逐文件累计,``calls`` 为去重调用数。"""

    items = [event for event in events if event.get("op") == op]
    paths: list[str] = []
    calls: list[str] = []
    for item in items:
        call = str(item.get("call") or "")
        if call and call not in calls:
            calls.append(call)
        for path in item.get("paths") or []:
            if path not in paths:
                paths.append(path)
    return {"calls": len(calls),
            "file_ops": sum(len(item.get("paths") or []) for item in items),
            "paths": paths}


def fingerprint(value: Any) -> str:
    """内容身份:已是 SHA-256 就直接用,否则按内容计算;None 记为 absent。"""

    if value is None:
        return "absent"
    text = str(value)
    return text if len(text) == 64 else sha256_text(text)


def baseline_changed(path: str, fingerprint_text: str,
                     state: dict[str, Any]) -> bool:
    """该路径的基准声明与本次给出的身份不同:属于外部修改引用目标。"""

    listed = (state.get("baseline") or {}).get(path)
    return listed is not None and str(listed) != fingerprint_text


def begin_gaps(context: dict[str, Any]) -> tuple[list[str], list[dict], list]:
    """开始或恢复的核对缺口:只涉及当前目标、授权、决定与未决项。

    返回 ``(gaps, pending, decisions)``;无关模块不进入核对范围。
    """

    gaps: list[str] = []
    if not str(context.get("mode") or ""):
        gaps.append("缺少工作模式")
    if not str(context.get("stage") or ""):
        gaps.append("缺少实际项目阶段")
    if not str(context.get("goal") or ""):
        gaps.append("缺少当前目标")
    if not str(context.get("module") or ""):
        gaps.append("缺少当前模块")
    if not str(context.get("entry") or ""):
        gaps.append("缺少资料入口")
    resolved = dict(context.get("resolved") or {})
    gaps.extend(f"未决项未说明:{unit}"
                for unit in (context.get("unresolved") or [])
                if not resolved.get(str(unit)))
    pending = [dict(item) for item in (context.get("pending") or [])
               if str(item.get("status") or "") in {"", "open", "未决"}
               and not item.get("impact")]
    if pending:
        gaps.append("未决项缺少对当前工作的影响:"
                    + "、".join(str(item.get("qid") or "")
                               for item in pending))
    return gaps, pending, list(context.get("decisions") or [])


def in_scope(state: dict[str, Any], item: dict[str, Any]) -> bool:
    """适用范围:当前模块资料与当前模块的必要依赖进入核对范围。"""

    module = str(item.get("module") or "")
    if not module:
        return True
    if module == str(state.get("module") or ""):
        return True
    names = {str(dep.get("id") if isinstance(dep, dict) else dep)
             for dep in (state.get("deps") or [])}
    return module in names


def scope_paths(state: dict[str, Any]) -> list[str]:
    """当前模块的已读路径:缺省失效范围,无关模块不被波及。"""

    module = str(state.get("module") or "")
    return [path for path, item in sorted((state.get("reads") or {}).items())
            if str(item.get("module") or "") == module]


def scope_path_keys(state: dict[str, Any]) -> list[str]:
    return list((state.get("reads") or {}).keys())


def result_affected(result: dict[str, Any], affected: list[str]) -> bool:
    """该检查结果是否依赖受影响路径。"""

    deps = [str(value) for value in
            (result.get("depends_on") or result.get("inputs") or [])]
    return any(path and path in deps for path in affected)


def target_paths(target: str | None) -> list[str]:
    """写入目标:单个路径,或 ``{path: content}`` 形式的多目标集合。"""

    if not target:
        return []
    text = str(target)
    if text.startswith("{"):
        try:
            loaded = json.loads(text)
        except ValueError:
            return [text]
        if isinstance(loaded, dict):
            return [str(key) for key in sorted(loaded)]
    return [text]


def within(path: str, pattern: str) -> bool:
    """资源范围匹配:``dir/**`` 覆盖其下全部文件,其余按精确匹配。"""

    if pattern.endswith("/**"):
        return path.startswith(pattern[:-3].rstrip("/") + "/")
    return path == pattern


def references(text: str) -> list[str]:
    """本次内容里出现的文档引用(模块规格、记录、基线)。"""

    refs: list[str] = []
    for token in re.split(r"[\s，。；、（）:：,;`*]+", str(text or "")):
        cleaned = token.strip()
        if cleaned.endswith(".md") and "/" in cleaned \
                and cleaned not in refs:
            refs.append(cleaned)
    return refs


def adopts_all_recommendations(text: str) -> bool:
    """整体采纳:出现采纳用语且没有否定或先讨论。"""

    return bool(OVERALL_RE.search(text)) and not REJECT_OVERALL_RE.search(text)


def is_unknown_value(value: str) -> bool:
    return bool(UNKNOWN_VALUE_RE.fullmatch(str(value or "").strip()))


def definite_choices(text: str) -> list[tuple[str, str]]:
    """明确的逐题选项;『选 A 还是 B』或尚未决定不算作答。"""

    items: list[tuple[str, str]] = []
    for match in CHOICE_RE.finditer(text):
        rest = text[match.end():]
        clause = re.split(r"[。；\n]", rest, maxsplit=1)[0]
        if re.match(r"\s*还是", rest) or re.search(r"还是|还没决定|不确定", clause):
            continue
        items.append((match.group(1), match.group(2).upper()))
    return items


def answers_from_reply(reply: str,
                       shown: Iterable[str] | None = None) -> dict[str, str]:
    """本轮实际答案:从用户回复解析 Q 编号与取值,供保存前核对。"""

    text = str(reply or "").strip()
    shown_list = [str(item) for item in (shown or [])]
    answers: dict[str, str] = {}
    if not text:
        return answers
    if adopts_all_recommendations(text):
        for qid in shown_list:
            answers.setdefault(qid, "recommendation")
    for qid, letter in definite_choices(text):
        answers[qid] = letter
    for match in ADJUST_RE.finditer(text):
        value = match.group(2).strip()
        if re.fullmatch(r"选\s*[A-Za-z]", value) or is_unknown_value(value):
            continue
        answers[match.group(1)] = value
    return answers


def adoption_gaps(answers: dict[str, str],
                  adopted: dict[str, Any]) -> list[str]:
    """采纳范围与来源:不在本轮答案内的不得采纳;来源必须可辨认。

    改口(revision)来自独立记录而非回复文本,不要求出现在解析结果中;
    其余来源必须在回复里找到对应作答,且内容一致。
    """

    gaps: list[str] = []
    for qid, item in adopted.items():
        source = str((item or {}).get("source") or "")
        if source == "prior":
            continue
        if source not in ANSWER_SOURCES:
            gaps.append(f"{qid} 缺少可辨认的采纳来源")
            continue
        if qid in answers:
            if not _value_matches(answers[qid], item):
                gaps.append(f"{qid} 采纳内容与本轮实际答案不一致")
        elif source != "revision":
            gaps.append(f"{qid} 不在本轮实际答案内,不得采纳")
    return gaps


def _value_matches(answer: str, item: Any) -> bool:
    """采纳内容与作答一致:选项字母按前缀核对,自定方案按包含核对。

    整体采纳(``recommendation``)只要求该问题出现在本轮回复覆盖范围内。
    """

    if answer == "recommendation":
        return True
    actual = str((item or {}).get("value") or "")
    if len(answer) <= 2:  # 选项字母:A / B …(渲染为「字母 + 选项全文」)
        return actual.split(maxsplit=1)[0].upper() == answer.upper() \
            if actual else False
    return answer == actual or answer in actual


def contradictions(adopted: dict[str, Any],
                   history: dict[str, Any]) -> list[str]:
    """与已有相关决定的矛盾:同题不同内容且未说明替代关系。"""

    failures: list[str] = []
    for qid, item in adopted.items():
        old = history.get(qid)
        if not old:
            continue
        old_value = old.get("value") if isinstance(old, dict) else old
        if isinstance(old, dict) and old.get("superseded"):
            continue
        new_value = (item or {}).get("value")
        if old_value == new_value:
            continue
        source = str((item or {}).get("source") or "")
        if source in {"revision", "prior"} or (item or {}).get("replaces"):
            continue
        failures.append(f"{qid} 与已有决定「{old_value}」矛盾且未说明替代关系")
    return failures


def entry_failures(recorded: str, parsed: dict[str, Any],
                   entries: list[dict[str, Any]],
                   pending: Iterable[dict] | None,
                   history: Iterable[Any] | None = None) -> list[str]:
    """回读核对:决定头完整且唯一、未决项/同步状态在记录中、历史保留。"""

    failures: list[str] = []
    for entry in entries:
        head = f"·{entry['qid']} {entry['title']}：采纳 {entry['value']}"
        count_heads = recorded.count(head)
        if count_heads == 0:
            failures.append(f"回读缺少决定:{entry.get('qid')}")
        elif count_heads > 1:
            failures.append(f"回读出现重复决定:{entry.get('qid')}")
    if entries and recorded.count(f"同步状态：{SYNC_PENDING}") < len(entries):
        failures.append("回读缺少本轮决定的同步状态标注")
    for item in (pending or []):
        qid = str(item.get("qid") or "")
        if qid and qid not in parsed["pending_qids"]:
            failures.append(f"回读缺少未决项:{qid}")
    for item in (history or []):
        value = str((item or {}).get("value") if isinstance(item, dict)
                    else item)
        if value and value not in recorded:
            failures.append(f"回读丢失历史:{value}")
    if (entries or pending) and not parsed["found"]:
        failures.append("回读内容不含本模块记录小节")
    return failures


def reference_failures(text: str, state: dict[str, Any], module: str,
                       known_paths: Iterable[str] | None = None) -> list[str]:
    """新改引用:本次内容里出现的引用必须可在现有入口定位。"""

    locatable = set(state.get("baseline") or {}) | set(state.get("reads") or {})
    locatable |= {str(item) for item in (known_paths or [])}
    missing = [ref for ref in references(text)
               if ref not in locatable
               and in_scope(state, {"path": ref, "module": module})]
    return ([f"新改引用不可定位:{'、'.join(missing)}"] if missing else [])


def forget_target(state: dict[str, Any], target: str | None) -> list[str]:
    """外部修改了引用目标:丢掉该目标的旧读取身份与依赖它的检查结果。"""

    stale: list[str] = []
    for path in target_paths(target):
        if path in (state.get("reads") or {}):
            state["reads"] = {key: item
                              for key, item in state["reads"].items()
                              if key != path}
            stale.append(path)
    state["target_version"] = None
    state["results"] = [
        {**item, "stale": True} if result_affected(item, target_paths(target))
        else item for item in (state.get("results") or [])]
    return stale


def parsed_module_record(text: str, module: str) -> dict[str, Any]:
    """记录解析的统一入口(本模块不另写一套格式解释)。"""

    return parse_record(text, module)


def impact_items(plan: dict[str, Any]) -> list[Any]:
    """收敛核对的影响项:必须同步项优先,其次显式影响列表。"""

    impact = plan.get("impact") or {}
    if isinstance(impact, dict):
        return list(impact.get("must_sync") or plan.get("must_sync") or [])
    return list(impact)


def paths(files: Any) -> list[str]:
    """文件计划 → 路径清单。"""

    return [str((item or {}).get("path") or "") for item in (files or [])]

def precheck_signature(answers: dict[str, str], adopted: dict[str, Any],
                       scope: set[str], target: str, path: str | None,
                       history: dict[str, Any]) -> str:
    """本次保存前核对的输入身份:回复、采纳、范围、目标版本与历史。"""

    return sha256_text(json.dumps(
        [answers, sorted((str(qid), str((item or {}).get("value")),
                          str((item or {}).get("source")))
                         for qid, item in adopted.items()),
         sorted(scope), target, path or "",
         sorted((str(qid), str((item or {}).get("value")))
                for qid, item in history.items())],
        ensure_ascii=False, default=str))


def presave_gaps(state: dict[str, Any], answers: dict[str, str],
                 adopted: dict[str, Any], history: dict[str, Any],
                 scope: set[str], path: str | None,
                 target: str) -> tuple[list[str], list[str]]:
    """保存前缺口与外部改动造成的失效:范围未知时交给受控通道逐次核对。"""

    gaps: list[str] = []
    gaps.extend(adoption_gaps(answers, adopted))
    gaps.extend(contradictions(adopted, history))
    if scope and path and not any(within(str(path), pattern)
                                  for pattern in scope):
        gaps.append(f"写入目标不在当前可写范围:{path}")
    stale: list[str] = []
    if state.get("target_version") is not None \
            and target != state["target_version"]:
        gaps.append("外部修改了引用目标:目标版本已变化,"
                    "先重新读取实际内容再决定")
        stale = forget_target(state, path or target)
    return gaps, stale
