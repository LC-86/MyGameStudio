#!/usr/bin/env python3
"""根据 identity / metrics / environment 写出票 01 基线报告。不宣称提速通过。"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(path: Path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_ms(value) -> str:
    if isinstance(value, int):
        return f"{value} ms"
    return str(value)


def section(name: str, metrics: dict | None, observed: dict | None) -> list[str]:
    lines = [f"## {name}", ""]
    if metrics is None:
        lines += ["未采集或缺少 metrics 文件。", ""]
        return lines
    comp = metrics.get("comparability") or {}
    lines.append(f"- 可比: **{comp.get('comparable')}** {comp.get('reason') or ''}".rstrip())
    mod = metrics.get("module") or {}
    lines.append(f"- 完整模块处理用时: {fmt_ms(mod.get('processing_ms'))}")
    lines.append(f"- 模块累计决定保存用时: {fmt_ms(mod.get('cumulative_decision_save_ms'))}")
    lines.append(f"- 扣除用户/轮间等待: {fmt_ms(mod.get('user_wait_ms_deducted'))}")
    lines.append("")
    lines.append("| 轮次 | 有采纳 | 决定保存 | 继续讨论等待 | 重试 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in metrics.get("rounds") or []:
        lines.append(
            f"| {row.get('index')} | {row.get('has_adopted_content')} | "
            f"{fmt_ms(row.get('decision_save_ms'))} | "
            f"{fmt_ms(row.get('continue_wait_ms'))} | {row.get('retried')} |"
        )
    steps = metrics.get("steps") or {}
    reads = steps.get("reads") or {}
    writes = steps.get("writes") or {}
    checks = steps.get("checks") or {}
    tools = steps.get("tool_calls") or {}
    lines += [
        "",
        f"- 讨论回合: {steps.get('discussion_rounds')}",
        f"- 读取: {reads.get('count')} 次 / {reads.get('bytes')} 字符"
        f"(必要 {reads.get('necessary')}, 重复 {reads.get('repeat')})",
        f"- 写入: {writes.get('count')} 次 / {writes.get('files')} 个文件",
        f"- 检查: {checks.get('count')}(必要 {checks.get('necessary')}, 重复 {checks.get('repeat')})",
        f"- 工具调用: {tools.get('count')}",
        f"- Token: {steps.get('tokens')}",
        "",
        "### 例外(单列)",
        "",
    ]
    exceptions = metrics.get("exceptions") or []
    if not exceptions:
        lines.append("无。")
    else:
        for item in exceptions:
            lines.append(f"- `{item.get('kind')}`: {item.get('detail')}")
    if observed:
        lines += ["", "### 成果回读", "",
                  f"- 写入路径: {observed.get('written_paths')}",
                  f"- 语义核对: {observed.get('semantics_matched')}",
                  f"- 说明: {observed.get('notes') or '—'}",
                  ]
    lines.append("")
    return lines


def main() -> int:
    ident = load(HERE / "results" / "identity.json") or {}
    env = (HERE / "results" / "environment.txt").read_text(encoding="utf-8") \
        if (HERE / "results" / "environment.txt").is_file() else "(无 environment.txt)\n"
    new_m = load(HERE / "results" / "new-design.metrics.json")
    chg_m = load(HERE / "results" / "existing-change.metrics.json")
    new_o = load(HERE / "results" / "new-design" / "observed.json")
    chg_o = load(HERE / "results" / "existing-change" / "observed.json")
    lines = [
        "# 票 01 基线报告:固定场景的优化前耗时与步骤",
        "",
        "**结论:本票只交付测量能力与优化前证据,不报告统一框架效率验收通过。**",
        "",
        "若任一类场景存在 `external_fault`、`missing_record` 或 `incomparable`,",
        "其完整模块用时**不得**作为有效效率基准,第 09 票结论只能是「效率尚未验证」。",
        "",
        "## 优化前内容身份",
        "",
        f"- 插件版本: {ident.get('plugin_version')}",
        f"- 插件树 SHA-256: {ident.get('plugin_tree_sha256')}",
        f"- Git 标签: {ident.get('git_tag')}(不以标签为前提)",
        f"- 模型: {ident.get('model')}",
        f"- 推理设置: {ident.get('reasoning')}",
        f"- 工具: {ident.get('tools')}",
        f"- 权限: {ident.get('permissions')}",
        f"- 说明: {ident.get('note')}",
        "",
        "关键文件指纹:",
        "",
    ]
    for rel, digest in (ident.get("content_sha256") or {}).items():
        lines.append(f"- `{rel}`: `{digest}`")
    lines += ["", "## 宿主与会话初始条件", "", "```", env.rstrip(), "```", ""]
    lines += section("新设计场景(gear-city / 每日挑战核心模块)", new_m, new_o)
    lines += section("已有设计变更场景(tide-pool / 海鸥干扰)", chg_m, chg_o)
    lines += [
        "## 给第 09 票",
        "",
        "- 比较时使用 `scenarios/*.md` 的同一答案语义与成果范围,以及 `caliber.md`。",
        "- 真实耗时只采用 `results/*/n*-events.jsonl` 与 `c*-events.jsonl`。",
        "- `fixtures/` 与测试里的合成事件只核口径。",
        "- 任一类标不可比、缺记录或环境干扰时,效率结论只能是「尚未验证」。",
        "",
    ]
    out = HERE / "BASELINE-REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
