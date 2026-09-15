#!/usr/bin/env python3
"""受控通道的单文件提交(统一设计问答框架票 05 从票 03/04 抽出)。

公开 interface:
  commit_path(channel, readback, *, path, content, expected_sha256, note) -> dict

保存(票 03)、模块规格交接(票 04)与完整设计交付(票 05)共用同一套写入
纪律:先按实际回读核对目标版本,再按当前授权核对可写范围,然后经受控通道
提交并回读确认。任一环节不成立都返回真实结果,由调用方用自己的计划语言
报告,不重试、不换通道或路径。缓存视图必须由通道逐次校验拒绝,本 module
不缓存授权或版本。
"""

from __future__ import annotations

from typing import Any, Callable

from decision_records import sha256_text


def commit_path(channel: Any, readback: Callable[[str], str | None], *,
                path: str, content: str, expected_sha256: str,
                note: str | None) -> dict[str, Any]:
    """提交一个文件:核对目标版本与当前授权,写入后回读。

    返回 ``{"ok": True, ...}`` 或 ``{"ok": False, "outcome": ...}``;
    失败结果带 ``rule_stage`` / ``reason`` / ``channel_result``。
    """

    actual = sha256_text(readback(path))
    if actual != expected_sha256:
        return {"ok": False, "outcome": "conflict", "path": path,
                "rule_stage": "version", "actual_sha256": actual,
                "reason": (f"{path} 已被改动"
                           f"（计划版本 {expected_sha256},实际 {actual}）")}
    scope = channel.scope()
    if scope.get("decision") != "allow":
        return {"ok": False, "outcome": "denied", "path": path,
                "denied_at": "scope", "scope": scope,
                "rule_stage": str(scope.get("rule_stage") or "identity"),
                "reason": (f"凭据不可写 {path}"
                           f"（rule_stage={scope.get('rule_stage')}）")}
    write_result = channel.write(path, content,
                                 expected_sha256=expected_sha256, note=note)
    if write_result.get("decision") != "allow":
        return {"ok": False, "outcome": "denied", "path": path,
                "denied_at": "channel",
                "rule_stage": write_result.get("rule_stage"),
                "reason": str(write_result.get("reason") or "写入被拒绝"),
                "channel_result": write_result}
    back = readback(path)
    if back is None or back != content:
        return {"ok": False, "outcome": "save_unconfirmed", "path": path,
                "reason": f"写入后回读核对失败（{path}）",
                "channel_result": write_result}
    return {"ok": True, "outcome": "saved", "path": path,
            "channel_result": write_result}
