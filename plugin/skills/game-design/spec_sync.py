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


def version_plan(meta: dict[str, Any], compare: dict[str, Any]) -> dict:
    """版本纪律:实质变化才递增;语义未变的调整按格式修正处理。"""

    announced = str(meta.get("change") or "").strip()
    from_v = str(meta.get("version_from") or "")
    to_v = str(meta.get("version_to") or from_v)
    if announced == "format" or (compare["previous_present"]
                                 and compare["semantic_equal"]):
        return {"from": from_v, "to": from_v, "change": "format",
                "note": f"本次仅为格式修正或语义一致的整理:版本保持 {from_v},"
                        f"不触发新版本,不算新产品要求。"}
    return {"from": from_v, "to": to_v, "change": "substantive",
            "note": f"本轮要求实质变化:{from_v} → {to_v};"
                    f"更新基线版本与双指纹并登记采纳依据。"}


def version_warnings(meta: dict[str, Any],
                     compare: dict[str, Any]) -> list[str]:
    """声明与回读核对不一致时如实提示,不静默按声明执行。"""

    warnings: list[str] = []
    announced = str(meta.get("change") or "").strip()
    if announced == "substantive" and compare["previous_present"] \
            and compare["semantic_equal"]:
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
    if version["change"] == "substantive" and baseline_authorized(
            authorization):
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
    if authorization.get("write") and authorization.get("sync") \
            and decision["to_sync"] and record_path:
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


def design_document(existing: str | None, meta: dict[str, Any],
                    version: dict[str, Any], spec_path: str,
                    decision: dict[str, Any]) -> str:
    """核心基线:引用模块规格,不重复具体规则;按既有规则登记双指纹。"""

    module = str(meta.get("module") or "")
    date = str(meta.get("date") or "")
    basis = adoption_basis(decision)
    relations = str(meta.get("system_relations")
                    or f"见模块规格 {spec_path} 的参与对象与前提,本文件不重复")
    lines = [f"# {module}：当前游戏需求与设计",
             "",
             f"维护责任：方案设计。基线版本：{version['to']}。"
             f"适用范围：{module}模块。采用依据：{basis}。",
             "",
             f"## 本轮可执行规格（{date}，{version['from']} → {version['to']}）",
             "",
             f"- 行为规则、边界、数值与验收：见模块规格 {spec_path}"
             f"（当前 {version['to']}；具体规则集中维护在那里,本文件只引用）。",
             f"- 与已有系统的关系：{relations}。",
             "- 技术约定：引用技术设计,不代写。",
             f"- 采纳依据：{basis}。",
             "",
             "## 验证与未决项",
             ""]
    pending = list(decision["pending"])
    if pending:
        for item in pending:
            lines.append(f"- {item['qid']} {item['title']}：{item['status']}。")
    else:
        lines.append("- 无。")
    lines.extend(["", "## 变更索引", "",
                  f"- {version['from']} → {version['to']}（{date}）："
                  f"新增{module}模块规格引用,采纳依据 {basis}。", "",
                  "内容指纹：sha256:" + "0" * 64,
                  "归一指纹：sha256:" + "0" * 64])
    return register_fingerprints("\n".join(lines) + "\n")


def register_fingerprints(text: str) -> str:
    """按既有双指纹规则登记:槽位占位后分别按原样与去空白计算。"""

    canonical = _FP_SLOT_RE.sub("sha256:<FP>", text)
    strict = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    norm = hashlib.sha256(
        "".join(canonical.split()).encode("utf-8")).hexdigest()
    return re.sub(r"内容指纹：sha256:[0-9a-f]{64}",
                  f"内容指纹：sha256:{strict}", text).replace(
        "归一指纹：sha256:" + "0" * 64, f"归一指纹：sha256:{norm}")


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
