#!/usr/bin/env python3
"""模块规格交接的版本、指纹与同步范围(统一设计问答框架票 04)。

决定"本轮同步哪些文件、基线写什么":模块规格、核心基线引用与版本、术语表、
决定记录的同步状态;其余资料保持零改动。版本纪律沿用既有规则——实质变化
递增版本并登记内容指纹与归一指纹(与 ``records/mgs_records.py`` 同一口径),
纯格式修正或语义一致的整理不触发新版本、不算新产品要求。具体规则集中维护
在模块规格,基线只引用。

本 module 只生成内容与版本判断,不写入、不接触受控通道(在 ``spec_draft``)。
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from decision_records import apply_sync, sha256_text
from spec_render import adoption_basis

_FP_SLOT_RE = re.compile(r"sha256:[0-9a-f]{64}")


def compare_existing(existing: str | None, spec_text: str,
                     present: bool) -> dict[str, Any]:
    """回读核对新旧规则:语义是否变化,不按实现重算规则内容。"""

    if not present or not existing:
        return {"previous_present": False, "semantic_equal": False,
                "existing_fingerprint": "absent",
                "spec_fingerprint": fingerprint(spec_text)}
    return {"previous_present": True,
            "semantic_equal": _semantics(existing) == _semantics(spec_text),
            "existing_fingerprint": fingerprint(existing),
            "spec_fingerprint": fingerprint(spec_text)}


def version_plan(meta: dict[str, Any], compare: dict[str, Any],
                 *, baseline_text: str | None = None, spec_path: str = "",
                 to_sync: list[str] | None = None) -> dict:
    """版本纪律:实质变化才递增;语义未变的调整按格式修正处理。

    规格正文相同不能证明核心基线已同步:仍有未同步决定且基线引用未指向
    当前版本(含从未引用)时,保持实质变化,继续规划基线写入。
    """

    announced = str(meta.get("change") or "").strip()
    from_v = str(meta.get("version_from") or "")
    to_v = str(meta.get("version_to") or from_v)
    if announced == "format" and compare["previous_present"] \
            and not compare["semantic_equal"]:
        return {"from": from_v, "to": from_v, "change": "conflict",
                "note": "声明为格式修正,但回读核对显示规则内容有实质变化;"
                        "先解决声明与实际内容的矛盾,再允许同步。"}
    if announced == "format" or (compare["previous_present"]
                                 and compare["semantic_equal"]):
        if _baseline_still_needs_spec(baseline_text, spec_path, to_sync,
                                      to_v):
            return {"from": from_v, "to": to_v, "change": "substantive",
                    "note": f"规格正文未变,但核心基线未引用该规格的"
                            f"当前版本 {to_v};仍按实质变化同步基线:"
                            f"{from_v} → {to_v}。"}
        return {"from": from_v, "to": from_v, "change": "format",
                "note": f"本次仅为格式修正或语义一致的整理:版本保持 {from_v},"
                        f"不触发新版本,不算新产品要求。"}
    return {"from": from_v, "to": to_v, "change": "substantive",
            "note": f"本轮要求实质变化:{from_v} → {to_v};"
                    f"更新基线版本与双指纹并登记采纳依据。"}


def _baseline_still_needs_spec(baseline_text: str | None, spec_path: str,
                               to_sync: list[str] | None,
                               version_to: str = "") -> bool:
    """仍有未同步决定时,基线引用是否还欠一次同步。

    判断依据是基线对**当前版本**的引用(旧版本引用不算新修订已同步),
    不能只看规格路径是否出现过。
    """

    if not spec_path or not to_sync:
        return False
    return not baseline_cites_spec(baseline_text, spec_path, version_to)


def baseline_cites_spec(baseline_text: str | None, spec_path: str,
                        version_to: str) -> bool:
    """核心基线对该规格的引用是否指向当前版本。

    只认**直接附着**在路径上的版本(紧随的括号或紧邻片段),不跨分隔符、
    表格列或链接目标去匹配其他模块的版本;引用缺失或仍指旧版本时,
    本轮修订不能当作已同步。
    """

    text = baseline_text or ""
    if not spec_path or not _has_path(text, spec_path):
        return False
    if not version_to:
        return True
    for line in text.split("\n"):
        if _attached_version(line, spec_path) == version_to:
            return True
    return False


def version_warnings(meta: dict[str, Any],
                     compare: dict[str, Any],
                     version: dict[str, Any] | None = None) -> list[str]:
    """声明与回读核对不一致时如实提示,不静默按声明执行。"""

    warnings: list[str] = []
    announced = str(meta.get("change") or "").strip()
    decided = str((version or {}).get("change") or "")
    if announced == "substantive" and compare["previous_present"] \
            and compare["semantic_equal"]:
        if decided == "substantive":
            warnings.append(
                "规格正文未变,但核心基线未引用该规格的当前版本;"
                "仍按实质变化同步基线,不把未完成同步当成格式修正。")
        else:
            warnings.append(
                "计划按实质变化递增版本,但回读核对显示新旧规则语义一致;"
                "已按格式修正处理,版本保持不变。")
    elif announced == "format" and compare["previous_present"] \
            and not compare["semantic_equal"]:
        warnings.append(
            "计划按格式修正处理,但回读核对显示规则内容有变化;"
            "请核对是否应递增版本,不要用格式修正掩盖实质变化。")
    return warnings


def sync_files(meta: dict[str, Any], parsed: dict[str, Any],
               decision: dict[str, Any], version: dict[str, Any],
               spec_text: str, existing: dict[str, str | None],
               authorization: dict[str, Any]) -> list[dict[str, Any]]:
    """只同步实际受影响的资料:规格、核心基线、术语表、决定记录同步状态。"""

    files: list[dict[str, Any]] = []
    spec_path = str(meta.get("spec_path") or "")
    design_path = str(meta.get("design_path") or "")
    glossary_path = str(meta.get("glossary_path") or "")
    record_path = str(meta.get("record_path") or "")
    files.append({"path": spec_path, "role": "模块规格",
                  "content": spec_text,
                  "expected_sha256": sha256_text(existing.get(spec_path))})
    needs_baseline = version["change"] == "substantive" or (
        _baseline_still_needs_spec(
            existing.get(design_path), spec_path,
            list(decision.get("to_sync") or []),
            str(version.get("to") or "")))
    if needs_baseline and baseline_authorized(authorization):
        design_text = design_document(existing.get(design_path), meta, version,
                                      spec_path, decision)
        files.append({"path": design_path, "role": "核心基线",
                      "content": design_text,
                      "expected_sha256": sha256_text(existing.get(design_path)),
                      "version": dict(version)})
    glossary = list(meta.get("glossary") or [])
    if glossary and glossary_path:
        files.append({"path": glossary_path, "role": "术语表",
                      "content": glossary_document(
                          existing.get(glossary_path), glossary),
                      "expected_sha256": sha256_text(
                          existing.get(glossary_path))})
    baseline_ready = baseline_cites_spec(
        existing.get(design_path), spec_path,
        str(version.get("to") or "")) or any(
            baseline_cites_spec(str(item.get("content") or ""), spec_path,
                                str(version.get("to") or ""))
            for item in files if item.get("role") == "核心基线")
    if authorization.get("write") and authorization.get("sync") \
            and decision["to_sync"] and record_path and baseline_ready:
        content, updated = apply_sync(existing.get(record_path) or "",
                                      str(meta.get("module") or ""),
                                      list(decision["to_sync"]),
                                      str(meta.get("date") or ""),
                                      str(meta.get("sync_ref") or ""))
        if updated:
            files.append({"path": record_path, "role": "决定记录同步状态",
                          "content": content,
                          "expected_sha256": sha256_text(
                              existing.get(record_path)),
                          "synced": sorted(updated)})
    return files


def baseline_authorized(authorization: dict[str, Any]) -> bool:
    """核心基线属于同步动作:缺少同步授权时只整理模块规格,不动基线。"""

    return bool(authorization.get("sync"))


_VERSION_HEADER_RE = re.compile(r"(基线版本\s*[:：]\s*)v\d+")
_FP_LINE_RE = re.compile(
    r"^(内容指纹|归一指纹)\s*[:：]\s*sha256:[0-9a-f]{64}\s*$")
_FP_TOKEN_RE = re.compile(
    r"(内容指纹|归一指纹)\s*[:：]\s*sha256:[0-9a-f]{64}[。.]?")


def design_document(existing: str | None, meta: dict[str, Any],
                    version: dict[str, Any], spec_path: str,
                    decision: dict[str, Any]) -> str:
    """核心基线:只更新受影响引用与索引,仍适用的既有内容保持原样。"""

    citation = _module_citation(meta, version, spec_path, decision)
    if not (existing or "").strip():
        return register_fingerprints(
            _new_baseline(meta, version, citation, decision))
    colon = _fingerprint_colon(existing)
    text = _strip_fingerprints(existing)
    text = _VERSION_HEADER_RE.sub(rf"\g<1>{version['to']}", text, count=1)
    text = _upsert_citation(text, spec_path, citation,
                            str(meta.get("module") or ""),
                            str(version.get("to") or ""))
    text = _append_index(text, meta, version, decision)
    return register_fingerprints(_ensure_fingerprint_slots(text, colon))


def _module_citation(meta: dict[str, Any], version: dict[str, Any],
                     spec_path: str, decision: dict[str, Any]) -> str:
    module = str(meta.get("module") or "")
    date = str(meta.get("date") or "")
    basis = adoption_basis(decision)
    relations = str(meta.get("system_relations")
                    or f"见模块规格 {spec_path} 的参与对象与前提,本文件不重复")
    return (f"## {module}模块规格引用（{date}，{version['from']} → "
            f"{version['to']}）\n\n"
            f"- 行为规则、边界、数值与验收：见模块规格 {spec_path}"
            f"（当前 {version['to']}；具体规则集中维护在那里,本文件只引用）。\n"
            f"- 与已有系统的关系：{relations}。\n"
            "- 技术约定：引用技术设计,不代写。\n"
            f"- 采纳依据：{basis}。\n")


def _new_baseline(meta: dict[str, Any], version: dict[str, Any],
                  citation: str, decision: dict[str, Any]) -> str:
    module = str(meta.get("module") or "")
    basis = adoption_basis(decision)
    lines = [f"# {module}：当前游戏需求与设计", "",
             f"维护责任：方案设计。基线版本：{version['to']}。"
             f"适用范围：{module}模块。采用依据：{basis}。", "",
             citation.rstrip(), "", "## 验证与未决项", ""]
    pending = list(decision["pending"])
    if pending:
        lines.extend(f"- {item['qid']} {item['title']}：{item['status']}。"
                     for item in pending)
    else:
        lines.append("- 无。")
    lines.extend(["", "## 变更索引", "", _index_line(meta, version, decision)])
    return "\n".join(lines) + "\n"


def _fingerprint_colon(text: str) -> str:
    """沿用已有登记的冒号形式;没有登记时用中文冒号。"""

    if re.search(r"(内容指纹|归一指纹):sha256:", text or ""):
        return ":"
    return "："


def _strip_fingerprints(text: str) -> str:
    stripped = _FP_TOKEN_RE.sub("", text)
    kept: list[str] = []
    for line in stripped.splitlines():
        if _FP_LINE_RE.match(line.strip()):
            continue
        if not line.strip():
            if kept and kept[-1] != "":
                kept.append("")
            continue
        kept.append(line.rstrip())
    return "\n".join(kept).rstrip() + "\n"


_SECTION_RE = re.compile(r"^## .*$(?:\n(?!## ).*)*", re.M)


def _upsert_citation(text: str, spec_path: str, citation: str,
                     module: str, version_to: str = "") -> str:
    """引用就位:只更新目标引用,保留仍适用的既有内容。

    生成器标准标题节原位替换;自定义标题的节做行内更新——只改规格
    路径旁的当前版本,同行其他字段、表格列与说明保持原样。重复引用
    只去掉路径与版本片段,不得删掉整行业务内容。规格路径已出现不能
    证明引用指向当前版本;引用位置保持唯一。
    """

    pattern = re.compile(
        rf"^## {re.escape(module)}模块规格引用.*$(?:\n(?!## ).*)*",
        re.M)
    if module and pattern.search(text):
        return pattern.sub(citation.rstrip(), text, count=1)
    ref_line = next((line for line in citation.splitlines()
                     if _has_path(line, spec_path)), citation.rstrip())
    for section in _SECTION_RE.finditer(text):
        body = section.group(0)
        if not _has_path(body, spec_path):
            continue
        return text[:section.start()] + _replace_reference_lines(
            body, spec_path, ref_line, version_to) + text[section.end():]
    if version_to and baseline_cites_spec(text, spec_path, version_to):
        return text
    if "## 变更索引" in text:
        return text.replace("## 变更索引",
                            citation.rstrip() + "\n\n## 变更索引", 1)
    return text.rstrip() + "\n\n" + citation


_CURRENT_VERSION_RE = re.compile(r"当前\s*(v\d+)")
# 本引用的版本片段:附着括号内容**顶层开头**的"当前 vN"(允许前导空白)。
# 版本前有其他文字(如"参照章节模块当前 v8")时,版本属于说明提到的
# 其他对象,不算本引用的版本。
_LEADING_VERSION_RE = re.compile(r"[ \t]*当前\s*(v\d+)")
# 完整路径身份:从出现位置向两侧扩展路径字符段得到完整 token,再与
# 规格路径比较——``archive/<PATH>``、``<PATH>.backup``、``<PATH>~``、
# ``<PATH>(backup)`` 都是不同文件;token 去掉 ``./`` 前缀与句末点号后
# 相同才算同一文件(``./<PATH>``、``<PATH>#锚点`` 是本规格的引用)。
# 中文不参与扩展:"详见<PATH>" 是自然语言紧邻,不是更长文件名。
_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_.\-~/]+")
# Markdown 内联链接目标:``](PATH)``、``](<PATH>)``、``]( PATH )``、
# ``](./<PATH>)`` 等;版本只能附着在链接闭括号之后,不进入目标或标题。
_LINK_BEFORE_RE = re.compile(r"\]\([ \t]*(?:[^\s()]*[ \t]*)?$")
# 引用式链接定义 ``[label]: <PATH> "标题"``:目标后紧跟可选标题,没有
# 能安全附着版本的位置——无既有附着版本时保持该行不动。
_LINKDEF_BEFORE_RE = re.compile(r"\]:[ \t]*(?:<)?[ \t]*$")
_BARE_VERSION_AFTER_RE = re.compile(
    r"[ \t]*(?:[，,、：:；;][ \t]*)?当前\s*(v\d+)")
_CITATION_LEAD_RE = re.compile(
    r"(?:行为规则、边界、数值与验收\s*[：:]\s*)?(?:见模块规格|详见)\s*$")


def _ascii_paren_span(text: str, pos: int) -> int | None:
    """pos 处紧邻路径的半角括号文件名段的结束位置。

    内容全为 ASCII 路径字符的 ``(backup)`` 是文件名的一部分;全角括号
    与带版本等非 ASCII 内容的半角括号(如 ``(当前 v3)``)不算文件名,
    留给附着版本处理。
    """

    if pos >= len(text) or text[pos] != "(":
        return None
    close = text.find(")", pos + 1)
    if close < 0:
        return None
    inner = text[pos + 1:close]
    if inner and _PATH_TOKEN_RE.fullmatch(inner):
        return close + 1
    return None


def _target_identity(raw: str, strip_dot: bool = True) -> str:
    """归一化的引用身份:去首尾空白、``./`` 前缀、``#锚点`` 与句末点号。

    ``strip_dot=False`` 用于明确的链接目标(``<…>``/``](…)``/引用式定义):
    目标里的句点属于文件名(``<PATH.>`` 指向另一个文件),不按正文句末剥除。
    """

    token = raw.strip()
    while token.startswith("./"):
        token = token[2:]
    token = token.split("#", 1)[0]
    return token.rstrip(".") if strip_dot else token


def _extends_filename(ch: str) -> bool:
    """紧邻路径后的非 ASCII 字母属于更长文件名(``PATH副本``),不是自然语言。

    路径前的中文是自然语言引导(``详见PATH``),不参与身份;路径后直接相连
    的中文/字母是文件名的一部分(``PATH副本``、``PATH草稿`` 是别的文件)。
    """

    return ord(ch) > 127 and unicodedata.category(ch)[0] == "L"


def _in_link_label(text: str, start: int, end: int) -> bool:
    """路径出现是否处于链接显示文字 ``[…](…)`` 内(不要求紧邻括号)。"""

    open_at = text.rfind("[", 0, start)
    if open_at < 0 or open_at < text.rfind("]", 0, start):
        return False
    close_at = text.find("]", end)
    return close_at >= 0 and text[close_at + 1:close_at + 2] == "("


def _linkdef_target(line: str, start: int, end: int) -> tuple[str, int] | None:
    """引用式链接定义 ``[label]: 目标 "标题"``:完整目标与可附着锚点。

    锚点是目标及可选标题之后的位置;定义行没有能安全插入新版本的
    地方,调用方只在该处已有附着版本时原位更新,否则保持不动。
    """

    prefix = _LINKDEF_BEFORE_RE.search(line[:start])
    if not prefix:
        return None
    pos = end
    if "<" in prefix.group(0):
        gt = line.find(">", pos)
        if gt < 0:
            return None
        target = line[start:gt]
        pos = gt + 1
    else:
        depth = 0
        while pos < len(line):
            ch = line[pos]
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            elif ch in " \t":
                break
            pos += 1
        target = line[start:pos]
    while pos < len(line) and line[pos] in " \t":
        pos += 1
    if pos < len(line) and line[pos] in "\"'":
        quote = line.find(line[pos], pos + 1)
        if quote >= 0:
            pos = quote + 1
    while pos < len(line) and line[pos] in " \t":
        pos += 1
    return target, pos


def _find_path(text: str, spec_path: str,
               from_pos: int = 0) -> tuple[int, int] | None:
    """完整路径身份的出现区间;更长文件名、显示文字与其他链接目标不算。"""

    pos = from_pos
    while True:
        start = text.find(spec_path, pos)
        if start < 0:
            return None
        end = start + len(spec_path)
        if _in_link_label(text, start, end):
            pos = start + 1  # 显示文字里的路径,目标里的才是引用
            continue
        tok_start = start
        while tok_start > 0 and _PATH_TOKEN_RE.fullmatch(text[tok_start - 1]):
            tok_start -= 1
        tok_end = end
        while True:
            while tok_end < len(text) and _PATH_TOKEN_RE.fullmatch(
                    text[tok_end]):
                tok_end += 1
            while tok_end < len(text) and _extends_filename(text[tok_end]):
                tok_end += 1  # 紧邻的非 ASCII 字母是更长文件名(PATH副本)
            span = _ascii_paren_span(text, tok_end)
            if span is None:
                break
            tok_end = span
        target_parts = _link_target_identity(text, tok_start, tok_end) \
            if _LINK_BEFORE_RE.search(text[:tok_start]) else None
        if target_parts is None:
            target_parts = _linkdef_target(text, tok_start, tok_end) \
                if _LINKDEF_BEFORE_RE.search(text[:tok_start]) else None
        if target_parts is not None:
            target = target_parts[0]
            if target is not None \
                    and _target_identity(target, strip_dot=False) != spec_path:
                pos = start + 1  # 完整目标指向其他文件(PATH副本/PATH（备份）)
                continue
            return tok_start, tok_end  # 目标解析不出时按命中,交调用方保守处理
        if _target_identity(text[tok_start:tok_end]) == spec_path:
            return tok_start, tok_end
        pos = start + 1


def _has_path(text: str, spec_path: str) -> bool:
    return _find_path(text, spec_path) is not None


def _link_target_identity(line: str,
                          start: int, end: int) -> tuple[str, int] | None:
    """内联链接目标的完整内容与链接闭括号位置;解析不出返回 None。

    目标可以是 ``<…>`` 包裹或裸形式(裸目标到空白或平衡括号外闭括号
    为止),其后允许可选空白与 ``"标题"``(标题里的括号不结束链接),
    最后才是链接闭括号。
    """

    prefix = _LINK_BEFORE_RE.search(line[:start])
    if not prefix:
        return None
    pos = end
    if "<" in prefix.group(0):
        gt = line.find(">", pos)
        if gt < 0:
            return None
        target = line[start:gt]
        pos = gt + 1
    else:
        depth = 0
        while pos < len(line):
            ch = line[pos]
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            elif ch in " \t":
                break
            pos += 1
        if pos >= len(line):
            return None
        target = line[start:pos]
    while pos < len(line) and line[pos] in " \t":
        pos += 1
    if pos < len(line) and line[pos] in "\"'":
        quote = line.find(line[pos], pos + 1)
        if quote < 0:
            return None
        pos = quote + 1
        while pos < len(line) and line[pos] in " \t":
            pos += 1
    if pos < len(line) and line[pos] == ")":
        return target, pos
    return None


def _link_close(line: str, start: int, end: int) -> int | None:
    """路径在内联链接目标内时,返回链接闭括号的位置。"""

    parts = _link_target_identity(line, start, end)
    return parts[1] if parts else None


def _match_bracket(line: str, pos: int) -> tuple[str, str, str, int] | None:
    """pos 起(允许空白)的成对括号:开括号、内容、闭括号、结束位置。

    深度计数配对,嵌套括号是内容的一部分;未闭合到行尾不算附着括号。
    """

    i = pos
    while i < len(line) and line[i] in " \t":
        i += 1
    if i >= len(line) or line[i] not in "（(":
        return None
    open_ch = line[i]
    depth = 1
    for j in range(i + 1, len(line)):
        ch = line[j]
        if ch in "（(":
            depth += 1
        elif ch in "）)":
            depth -= 1
            if depth == 0:
                return open_ch, line[i + 1:j], ch, j + 1
    return None


def _top_level_version(inner: str) -> tuple[str, int, int] | None:
    """本引用的版本:附着括号内容**顶层开头**的"当前 vN"。

    版本前有其他文字(如"参照章节模块当前 v8 的规则")时,版本属于
    说明提到的其他对象;嵌套括号里的版本属于嵌套内容。两种情况都
    不算本引用的版本,由调用方原样保留、不改不删。
    """

    cut = len(inner)
    for i, ch in enumerate(inner):
        if ch in "（(":
            cut = i
            break
    found = _LEADING_VERSION_RE.match(inner, 0, cut)
    if found:
        return found.group(1), found.start(), found.end()
    return None


def _code_span(line: str, start: int,
               end: int) -> tuple[str, int, int]:
    """行内代码片段包裹状态:返回 (状态, 闭反引号串之后, 开反引号串起点)。

    状态 ``ok`` 为成对包裹(单/双/多反引号,允许反引号与路径间有空白,
    闭串在路径后);``broken`` 为紧邻路径的开串存在但无等长闭串,无法安全
    定位版本位置,调用方保持不动;``none`` 为未被反引号包裹。
    """

    runs: list[tuple[int, int]] = []
    i, n = 0, len(line)
    while i < n:
        if line[i] == "`":
            j = i
            while j < n and line[j] == "`":
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    # 成对代码片段:开串与下一个等长闭串配对(CommonMark),路径须落在其间。
    # 反引号与路径间可有空格(`` ` PATH ` ``),故按完整片段而非紧邻判断。
    k = 0
    while k < len(runs):
        op_pos, op_len = runs[k]
        m = k + 1
        while m < len(runs) and runs[m][1] != op_len:
            m += 1
        if m >= len(runs):
            break
        cl_pos, cl_len = runs[m]
        if op_pos + op_len <= start and end <= cl_pos:
            return "ok", cl_pos + cl_len, op_pos
        k = m + 1
    # 未落在成对片段内:仅当开串紧邻路径(无空白)才算 broken——
    # 远处散落的反引号是正文,不影响本路径。
    opens = 0
    i = start - 1
    while i >= 0 and line[i] == "`":
        opens += 1
        i -= 1
    closes = 0
    while end + closes < n and line[end + closes] == "`":
        closes += 1
    if not opens:
        return "none", end, start
    if opens == closes:
        return "ok", end + closes, start - opens
    return "broken", end, start - opens


def _attached_version(line: str, spec_path: str) -> str:
    """直接附着在路径上的当前版本号;不属于本引用的版本不匹配。

    版本只认完整路径身份上的附着:紧随路径的成对括号**顶层**,或经
    至多一个分隔符紧邻的裸版本;路径在链接目标内时附着在链接闭括号
    之后。更长文件名(如 ``.backup``)、嵌套括号里其他模块的版本都
    不算本引用的版本。
    """

    found = _find_path(line, spec_path)
    if not found:
        return ""
    start, end = found
    code_status, code_after, _ = _code_span(line, start, end)
    if code_status == "broken":
        return ""  # 反引号不配对:没有可安全认定的版本位置
    if code_status == "ok":
        anchors = [code_after]  # 行内代码片段:版本附着在闭反引号串之后
    elif _LINKDEF_BEFORE_RE.search(line[:start]):
        parts = _linkdef_target(line, start, end)
        if parts is None:
            return ""
        bracket = _match_bracket(line, parts[1])
        top = _top_level_version(bracket[1]) if bracket else None
        return top[0] if top else ""
    else:
        anchors = [end]
        close = _link_close(line, start, end)
        if close is not None:
            anchors = [close + 1]  # 目标内不认附着,版本只在闭括号之后
    for after in anchors:
        bracket = _match_bracket(line, after)
        if bracket:
            top = _top_level_version(bracket[1])
            if top:
                return top[0]
            continue
        bare = _BARE_VERSION_AFTER_RE.match(line, after)
        if bare:
            return bare.group(1)
    return ""


def _version_in_ref_line(ref_line: str) -> str:
    match = _CURRENT_VERSION_RE.search(ref_line)
    return match.group(1) if match else ""


def _update_line_citation(line: str, spec_path: str, version_to: str) -> str:
    """只更新本引用的版本:范围限于附着括号顶层或紧邻的裸版本片段。

    版本必须落在链接目标之外;链接后已有附着括号时原位更新其中顶层
    版本,不追加第二个当前版本;嵌套括号里其他模块的版本不动。
    """

    found = _find_path(line, spec_path)
    if not found or not version_to:
        return line
    start, end = found
    code_status, code_after, _ = _code_span(line, start, end)
    if code_status == "broken":
        return line  # 反引号不配对:保持内容,由回读判定未完成
    if code_status == "ok":
        anchors = [code_after]  # 行内代码片段:版本插在闭反引号串之后
        insert_at = code_after
    elif _LINKDEF_BEFORE_RE.search(line[:start]):
        parts = _linkdef_target(line, start, end)
        if parts is None:
            return line
        bracket = _match_bracket(line, parts[1])
        top = _top_level_version(bracket[1]) if bracket else None
        if not top:
            return line  # 定义行无既有附着版本:没有安全位置,保持不动
        _, a, b = top
        open_ch, inner, close_ch, stop = bracket
        return (line[:parts[1]] + open_ch
                + inner[:a] + f"当前 {version_to}" + inner[b:]
                + close_ch + line[stop:])
    else:
        in_link = bool(_LINK_BEFORE_RE.search(line[:start]))
        close = _link_close(line, start, end)
        if in_link and close is None:
            return line  # 链接目标解析不出闭括号:保持内容,由回读判定未完成
        anchors = [close + 1] if close is not None else [end]
        insert_at = close + 1 if close is not None else end
    for after in anchors:
        bracket = _match_bracket(line, after)
        if bracket:
            open_ch, inner, close_ch, stop = bracket
            top = _top_level_version(inner)
            if top:
                new_inner = (inner[:top[1]] + f"当前 {version_to}"
                             + inner[top[2]:])
            elif inner.strip():
                new_inner = f"当前 {version_to}；{inner.strip()}"
            else:
                new_inner = f"当前 {version_to}"
            return (line[:after] + open_ch + new_inner + close_ch
                    + line[stop:])
        bare = _BARE_VERSION_AFTER_RE.match(line, after)
        if bare:
            old = _CURRENT_VERSION_RE.search(bare.group(0))
            return (line[:after] + bare.group(0)[:old.start()]
                    + f"当前 {version_to}" + line[after + old.end():])
    return line[:insert_at] + f"（当前 {version_to}）" + line[insert_at:]


def _drop_top_version(inner: str) -> str:
    """去掉括号顶层的版本片段及其紧邻分隔符,保留其余内容。

    嵌套括号里的其他模块版本属于业务条件;顶层没有本引用版本时,
    无法可靠分离就整体保留。
    """

    top = _top_level_version(inner)
    if not top:
        return inner.strip()
    lead = top[1]
    while lead > 0 and inner[lead - 1] in "；;，, \t":
        lead -= 1
    tail = top[2]
    while tail < len(inner) and inner[tail] in "；;，, \t":
        tail += 1
    left, right = inner[:lead], inner[tail:]
    if left and right:
        return (left + "；" + right).strip()
    return (left + right).strip()


def _clean_citation_remainder(head: str, tail: str) -> str:
    remainder = _CITATION_LEAD_RE.sub("", head) + tail
    remainder = re.sub(r"[ \t]{2,}", " ", remainder)
    remainder = re.sub(r"[；;]{2,}", "；", remainder)
    return remainder.rstrip()


def _strip_attached(line: str, pos: int) -> str:
    """链接闭括号后的附着版本:去掉顶层版本片段,保留业务条件。"""

    bracket = _match_bracket(line, pos)
    if bracket:
        open_ch, inner, close_ch, stop = bracket
        remainder = _drop_top_version(inner)
        if not remainder:
            return line[stop:]
        return open_ch + remainder + close_ch + line[stop:]
    bare = _BARE_VERSION_AFTER_RE.match(line, pos)
    return line[bare.end():] if bare else line[pos:]


def _strip_line_citation(line: str, spec_path: str) -> str:
    """去掉本行的重复引用(路径+附着版本),保留其余业务内容。

    链接形式的重复引用保留链接文字;附着括号内混有规则或其他模块
    版本时只去本引用的顶层版本,嵌套内容不吞。
    """

    found = _find_path(line, spec_path)
    if not found:
        return line
    start, end = found
    code_status, code_after, code_open = _code_span(line, start, end)
    if code_status == "broken":
        return line  # 反引号不配对:保持内容,由回读判定未完成
    if code_status == "ok":
        return _clean_citation_remainder(
            line[:code_open], _strip_attached(line, code_after))
    if _LINKDEF_BEFORE_RE.search(line[:start]):
        return line  # 引用式链接定义:保持不动,由回读判定未完成
    close = _link_close(line, start, end)
    if _LINK_BEFORE_RE.search(line[:start]) and close is None:
        return line  # 链接目标解析不出闭括号:保持内容,由回读判定未完成
    if close is not None:
        label_start = line.rfind("[", 0, start)
        label_close = line.rfind("]", 0, start)
        if label_start >= 0 and label_close > label_start:
            return _clean_citation_remainder(
                line[:label_start],
                line[label_start + 1:label_close]
                + _strip_attached(line, close + 1))
    bracket = _match_bracket(line, end)
    if bracket:
        open_ch, inner, close_ch, stop = bracket
        remainder = _drop_top_version(inner)
        if remainder:
            return _clean_citation_remainder(
                line[:start], open_ch + remainder + close_ch
                + line[stop:])
        return _clean_citation_remainder(line[:start], line[stop:])
    bare = _BARE_VERSION_AFTER_RE.match(line, end)
    strip_end = bare.end() if bare else end
    return _clean_citation_remainder(line[:start], line[strip_end:])


def _line_has_business_text(line: str) -> bool:
    """去掉 Markdown 结构后是否还有业务正文。"""

    text = re.sub(r"^[-*+]+\s+", "", line.strip())
    text = re.sub(r"^\d+[.)、]\s+", "", text)
    text = re.sub(r"\|", "", text)
    text = re.sub(r"^[-:\s]+$", "", text.strip())
    return bool(re.sub(r"[\s，,。．.；;：:、（）()]+", "", text))


def _in_multiline_link(body: str, spec_path: str) -> bool:
    """body 中 spec_path 是否落在跨行的内联链接目标 ``]( … )`` 内。

    CommonMark 允许链接目标跨行(``[文字](\\n PATH\\n)``)。逐行处理会把
    版本插进目标所在行、把有效链接拆成无链接,故检测到即整段保守不动。
    """

    i, n = 0, len(body)
    while True:
        idx = body.find("](", i)
        if idx < 0:
            return False
        open_paren = idx + 1
        depth, j = 0, open_paren
        while j < n:
            ch = body[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:
            return False  # 括号未闭合:不是可识别的链接
        inner = body[open_paren + 1:j]
        if "\n" in inner and spec_path in inner:
            return True
        i = j + 1


def _replace_reference_lines(body: str, spec_path: str,
                             ref_line: str, version_to: str = "") -> str:
    """行内更新引用:只改路径与版本片段,同行其余内容原样保留。"""

    if _in_multiline_link(body, spec_path):
        # 跨行链接目标无法逐行安全更新:保持原文,由回读判定未完成。
        return body
    updated: list[str] = []
    placed = False       # 已找到引用(更新或保守保留)→ 不再追加生成引用
    updated_ok = False   # 已确实更新到目标版本 → 其后视为重复引用
    target = version_to or _version_in_ref_line(ref_line)
    for line in body.split("\n"):
        if not _has_path(line, spec_path):
            updated.append(line)
            continue
        if not placed:
            # 无版本时也不得整行换成生成引用,以免删掉同行仍有效的规则。
            new_line = (_update_line_citation(line, spec_path, target)
                        if target else line)
            updated.append(new_line)
            placed = True
            updated_ok = bool(target) and new_line != line
            continue
        if updated_ok:
            # 目标引用已确认更新:其后是重复引用,去重但保留同行业务正文。
            remainder = _strip_line_citation(line, spec_path)
            if _line_has_business_text(remainder):
                updated.append(remainder)
            continue
        # 首条未能确认更新(引用式定义/不配对反引号/解析不出的链接):
        # 其后引用既非可确认的重复,就保持原文——不删除也不更新,
        # 由回读判定未完成,绝不把未确认的同步当成已完成。
        updated.append(line)
    if not placed:
        updated.append(ref_line)
    return "\n".join(updated)


def _append_index(text: str, meta: dict[str, Any], version: dict[str, Any],
                  decision: dict[str, Any]) -> str:
    line = _index_line(meta, version, decision)
    if line in text:
        return text
    if "## 变更索引" in text:
        return text.rstrip() + "\n" + line + "\n"
    return text.rstrip() + "\n\n## 变更索引\n\n" + line + "\n"


def _index_line(meta: dict[str, Any], version: dict[str, Any],
                decision: dict[str, Any]) -> str:
    return (f"- {version['from']} → {version['to']}"
            f"（{meta.get('date') or ''}）：新增{meta.get('module') or ''}"
            f"模块规格引用,采纳依据 {adoption_basis(decision)}。")


def _ensure_fingerprint_slots(text: str, colon: str = "：") -> str:
    body = text.rstrip()
    if not re.search(r"内容指纹\s*[:：]\s*sha256:", body):
        body += f"\n\n内容指纹{colon}sha256:" + "0" * 64
    if not re.search(r"归一指纹\s*[:：]\s*sha256:", body):
        body += f"\n归一指纹{colon}sha256:" + "0" * 64
    return body + "\n"


def register_fingerprints(text: str) -> str:
    """按既有双指纹规则登记:槽位占位后分别按原样与去空白计算。"""

    if not re.search(r"内容指纹\s*[:：]\s*sha256:", text):
        text = _ensure_fingerprint_slots(text)
    canonical = _FP_SLOT_RE.sub("sha256:<FP>", text)
    strict = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    norm = hashlib.sha256(
        "".join(canonical.split()).encode("utf-8")).hexdigest()
    text = re.sub(r"内容指纹(\s*[:：]\s*)sha256:[0-9a-f]{64}",
                  lambda match: f"内容指纹{match.group(1)}sha256:{strict}",
                  text, count=1)
    return re.sub(r"归一指纹(\s*[:：]\s*)sha256:[0-9a-f]{64}",
                  lambda match: f"归一指纹{match.group(1)}sha256:{norm}",
                  text, count=1)


def glossary_document(existing: str | None, entries: list[dict]) -> str:
    """术语表:保留既有条目,只追加已明确术语,不承担完整规格。"""

    text = (existing or "# 术语表\n").rstrip() + "\n"
    for entry in entries:
        term = str(entry.get("term") or "")
        if not term or f"{term}：" in text:
            continue
        text += (f"\n- {term}：{entry.get('meaning')}。"
                 f"来源：{entry.get('source')}。\n")
    return text


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _semantics(text: str) -> str:
    """语义比较口径:去标题层级、去空白的正文,格式差异不计。"""

    lines = [re.sub(r"^#{1,6}\s*", "", line).strip()
             for line in text.splitlines()]
    return "".join("".join(line.split()) for line in lines).replace("#", "")
