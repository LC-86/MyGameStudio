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

    引用条目在规格路径旁标明「当前 vN」;引用缺失或仍指旧版本时,
    本轮修订不能当作已同步。
    """

    text = baseline_text or ""
    if not spec_path or spec_path not in text:
        return False
    if not version_to:
        return True
    return bool(re.search(
        re.escape(spec_path) + r"[^\n]{0,60}当前\s*" + re.escape(version_to)
        + r"(?!\d)", text))


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

    生成器标准标题节原位替换;自定义标题的节做行级更新——只替换含该
    规格路径的行,同节其他规则、引用与说明保持原样。规格路径已出现
    不能证明引用指向当前版本;引用位置保持唯一。
    """

    pattern = re.compile(
        rf"^## {re.escape(module)}模块规格引用.*$(?:\n(?!## ).*)*",
        re.M)
    if module and pattern.search(text):
        return pattern.sub(citation.rstrip(), text, count=1)
    ref_line = next((line for line in citation.splitlines()
                     if spec_path in line), citation.rstrip())
    for section in _SECTION_RE.finditer(text):
        body = section.group(0)
        if spec_path not in body:
            continue
        return text[:section.start()] + _replace_reference_lines(
            body, spec_path, ref_line) + text[section.end():]
    if version_to and baseline_cites_spec(text, spec_path, version_to):
        return text
    if "## 变更索引" in text:
        return text.replace("## 变更索引",
                            citation.rstrip() + "\n\n## 变更索引", 1)
    return text.rstrip() + "\n\n" + citation


def _replace_reference_lines(body: str, spec_path: str,
                             ref_line: str) -> str:
    """行级更新引用:只替换含该规格路径的行,同节其余内容原样保留。"""

    updated: list[str] = []
    replaced = False
    for line in body.split("\n"):
        if spec_path not in line:
            updated.append(line)
            continue
        if replaced:
            continue  # 旧版本引用行去重,引用位置保持唯一
        updated.append(ref_line)
        replaced = True
    if not replaced:
        updated.append(ref_line)  # 路径跨行断开等罕见形态:追加,不删内容
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
