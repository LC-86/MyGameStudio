#!/usr/bin/env python3
"""Game-Design 四类交付内容的渲染(统一设计问答框架票 05)。

公开 interface:
  render_design(meta, material, coverage, journey) -> str
  render_content(existing, meta, material) -> str
  render_version(meta, material, coverage, journey) -> str
  deliverable_plan(meta, material, coverage, journey) -> list[dict]

四类交付内容:游戏设计主文档、系统规则与数值(引用模块规格的现行权威位置)、
内容与视听制作需求、版本与验证方案。沿用当前主文档与附表,不合并为单文件、
不重造文档体系;具体规则只引用权威位置,不在这里重复。版本与验证方案区分
概念说明、原型所需规格与当前版本完整设计,列出范围、依赖、验收、风险与
待验证事项及其是否阻断当前阶段;没有实际证据不写验证通过。

本 module 只渲染文本与文件计划,不判断授权、不接触受控通道(在 ``full_design``)。
"""

from __future__ import annotations

from typing import Any

from coverage_map import STAGE_LABELS, stage_status
from spec_sync import register_fingerprints

ROLE_DESIGN = "游戏设计主文档"
ROLE_SPECS = "系统规则与数值"
ROLE_CONTENT = "内容与视听制作需求"
ROLE_VERSION = "版本与验证方案"

CONTENT_SECTIONS = (
    ("levels_events", "关卡与事件结构"),
    ("templates", "内容模板"),
    ("characters", "角色"),
    ("scenes", "场景"),
    ("ui", "界面"),
    ("animation_vfx", "动画与特效"),
    ("audio", "声音需求"),
)


def render_design(meta: dict[str, Any], material: dict[str, Any],
                  coverage: dict[str, Any],
                  journey: dict[str, Any]) -> str:
    """游戏设计主文档:概述、核心体验、核心玩法、完整流程、系统关系与版本边界。"""

    game = str(meta.get("game") or material.get("game") or "")
    date = str(meta.get("date") or "")
    version = _version_label(meta)
    design = dict(material.get("design") or {})
    lines = [f"# {game}：游戏设计主文档", "",
             f"维护责任：方案设计。版本：{version}。日期：{date}。",
             f"本文件是全游戏的交付入口;现行规则集中在模块规格,本文件只引用,"
             f"不重复规则正文。", "",
             "## 总体概述", "", str(design.get("overview") or ""), "",
             "## 核心体验", "", str(design.get("core_experience") or ""), "",
             "## 核心玩法", "", str(design.get("core_loop") or ""), "",
             "## 完整游玩过程", ""]
    for step in journey.get("steps") or []:
        state = "已闭合" if step["status"] == "closed" else "未闭合"
        detail = step["detail"] or "未写明"
        lines.append(f"- {step['label']}：{detail}（{state}）")
    lines.extend(["", "## 系统与相互关系", "",
                  str(design.get("system_relations") or ""), "",
                  "## 版本边界", "", "### 当前成稿版本"])
    scope = dict(coverage.get("scope") or {})
    lines.extend(_bullet_lines(scope.get("current"), "text"))
    lines.extend(["", "### 后续方向"])
    lines.extend(_bullet_lines(scope.get("later"), None))
    lines.extend(["", "### 范围外内容"])
    lines.extend(_bullet_lines(scope.get("out_of_scope"), None))
    lines.extend(["", "### 完整愿景（不等于当前版本）"])
    lines.extend(_bullet_lines(scope.get("vision"), None))
    lines.extend(["", "## 交付入口（四类交付物）", ""])
    for path, role in deliverable_outputs(meta):
        note = ("（现行规则的唯一权威位置,本文件只引用）"
                if role == ROLE_SPECS else "")
        lines.append(f"- {role}：{path}{note}")
    lines.extend(["", f"入口：本文件（{meta.get('design_path') or ''}）。"])
    return register_fingerprints("\n".join(lines).rstrip() + "\n")


def render_content(existing: str | None, meta: dict[str, Any],
                   material: dict[str, Any]) -> str:
    """内容与视听制作需求:保留既有说明,追加本轮需求并与规则位置互指。"""

    text = (existing or "# 内容与视听制作需求\n").rstrip() + "\n"
    spec_path = (meta.get("module_specs") or [{}])[0].get("spec_path") or ""
    content = dict(material.get("content") or {})
    lines = ["", f"## 本轮内容与视听制作需求（{meta.get('date') or ''}）", ""]
    for key, title in CONTENT_SECTIONS:
        items = list(content.get(key) or [])
        if not items:
            continue
        lines.append(f"### {title}")
        for raw in items:
            item = dict(raw)
            rules = [str(rule) for rule in item.get("rules") or []]
            suffix = (f"（规则位置：{spec_path}·{'、'.join(rules)}）"
                      if rules and spec_path else "")
            lines.append(f"- {item.get('text')}{suffix}")
        lines.append("")
    lines.append("制作范围与相关规则可相互定位:规则只见模块规格,本文件写"
                 "需要制作的内容、表现与资产需求。")
    return text + "\n".join(lines).rstrip() + "\n"


def render_version(meta: dict[str, Any], material: dict[str, Any],
                   coverage: dict[str, Any],
                   journey: dict[str, Any]) -> str:
    """版本与验证方案:阶段与范围、依赖、验收场景、风险与待验证事项。"""

    game = str(meta.get("game") or material.get("game") or "")
    scope = dict(coverage.get("scope") or {})
    lines = [f"# {game}：版本与验证方案", "",
             f"维护责任：方案设计。日期：{meta.get('date') or ''}。"
             f"本文件说明当前阶段、范围、依赖、验收与待验证事项。", "",
             "## 阶段与范围", ""]
    lines.extend(_stage_lines(meta, material))
    lines.extend(["", "### 当前成稿版本范围"])
    lines.extend(_bullet_lines(scope.get("current"), "text"))
    lines.extend(["", "### 后续方向（不在当前版本）"])
    lines.extend(_bullet_lines(scope.get("later"), None))
    lines.extend(["", "### 范围外内容"])
    lines.extend(_bullet_lines(scope.get("out_of_scope"), None))
    lines.extend(["", "## 依赖", ""])
    lines.extend(_bullet_lines(material.get("dependencies"), None))
    lines.extend(["", "## 验收场景", ""])
    for case in material.get("acceptance") or []:
        item = dict(case)
        lines.append(f"- 初始条件：{item.get('initial')}")
        lines.append(f"  操作：{item.get('action')}")
        lines.append(f"  预期结果：{item.get('expected')}")
    lines.extend(["", "## 风险与待验证项", ""])
    lines.extend(_bullet_lines(material.get("risks"), None))
    lines.extend(_prototype_lines(material))
    lines.extend(["", "## 未知与待查事项", ""])
    lines.extend(_unknown_lines(coverage))
    lines.extend(["", "## 状态说明", "",
                  "- 实现状态：未实现（设计交付不自动授权制作,不自动启动制作）。",
                  "- 验证状态：未验证（没有原型或试玩证据,不报告相应验证通过）。"])
    return "\n".join(lines).rstrip() + "\n"


def _stage_lines(meta: dict[str, Any],
                 material: dict[str, Any]) -> list[str]:
    """概念说明、原型所需规格与当前版本完整设计:按所需成果判定并标当前阶段。"""

    current = str(meta.get("stage") or "current_version")
    lines: list[str] = []
    for stage, label in STAGE_LABELS.items():
        status = stage_status(material, stage=stage)
        marker = "（当前阶段）" if stage == current else ""
        lines.append(f"### {label}{marker}："
                     f"{'已完成' if status['complete'] else '未完成'}")
        if status["missing"]:
            lines.append("未达成：" + "、".join(status["missing"]))
    return lines


def _prototype_lines(material: dict[str, Any]) -> list[str]:
    """原型与试玩事项:目标、方法与判定依据,并标注是否阻断当前阶段。"""

    prototype = list(material.get("prototype") or [])
    if not prototype:
        return ["- 无需要原型或试玩的事项。"]
    lines: list[str] = []
    for raw in prototype:
        item = dict(raw)
        lines.append(f"- 验证问题：{item.get('question')}")
        lines.append(f"  验证目标：{item.get('goal')}")
        lines.append(f"  验证方法：{item.get('method')}")
        lines.append(f"  判定依据：{item.get('judgement')}")
        lines.append("  是否阻断当前阶段："
                     f"{'是' if item.get('blocks_stage') else '否'}")
        if item.get("evidence"):
            lines.append(f"  实际证据：{item['evidence']}")
        else:
            lines.append("  实际证据：无（没有原型或试玩证据,"
                         "不报告体验或市场效果已验证）")
    return lines


def _unknown_lines(coverage: dict[str, Any]) -> list[str]:
    """关键未知:方法与影响说明,不清楚时不写成不适用。"""

    unknown = [entry for entry in (coverage.get("domains") or {}).values()
               if entry["status"] == "unknown"]
    if not unknown:
        return ["- 无。"]
    return [f"- {entry['title']}："
            f"方法 {entry.get('method') or '尚未给出查证方法'}；"
            f"影响 {entry.get('impact') or '影响未单独说明'}。"
            for entry in unknown]


def deliverable_outputs(meta: dict[str, Any]) -> list[tuple[str, str]]:
    """四类交付物路径与角色:主文档为入口,其余三类为配套附表或权威位置。"""

    doc_map = dict(meta.get("doc_map") or {})
    spec_paths = [str(item.get("spec_path") or "")
                  for item in meta.get("module_specs") or []
                  if item.get("spec_path")]
    return [
        (str(doc_map.get("design") or ""), ROLE_DESIGN),
        (spec_paths[0] if spec_paths else "", ROLE_SPECS),
        (str(doc_map.get("content") or ""), ROLE_CONTENT),
        (str(doc_map.get("version") or ""), ROLE_VERSION),
    ]


def _bullet_lines(items: Any, key: str | None) -> list[str]:
    values = []
    for raw in items or []:
        text = str(raw.get(key) if key and isinstance(raw, dict) else raw)
        values.append(f"- {text}")
    return values or ["- 无。"]


def _version_label(meta: dict[str, Any]) -> str:
    from_version = str(meta.get("version_from") or "")
    to_version = str(meta.get("version_to") or from_version)
    if from_version and from_version != to_version:
        return f"{to_version}（{from_version} → {to_version}）"
    return to_version or from_version
