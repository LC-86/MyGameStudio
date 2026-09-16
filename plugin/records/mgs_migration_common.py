#!/usr/bin/env python3
"""本地迁移、GitHub 迁移与安全切换的共享私有助手(issue #73)。

``mgs_local_migration``、``mgs_github_material_migration`` 与
``mgs_safe_switch`` 此前各自维护同一组私有助手:文件指纹、相对路径、
幂等文本读写、待切换树定位、状态文件 JSON 读写、字段/小节/标题提取、
规格身份补章与 gate 历史留存。本模块是这些助手的唯一定义,消费方按
既有名字导入,公开接缝与行为不变。GitHub 迁移在共享的规格补章之外还
要加盖 pending-switch 章,由消费方在共享实现外自行组合,不在本模块。
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_record_source import DEFAULT_CONFIG_REL  # noqa: E402
from mgs_spec import SPEC_MARK  # noqa: E402

PENDING_REL = "docs/mygamestudio/records/pending-switch"
STATUS_NAME = "migration-status.json"
IDENTITY_NAME = "identity-map.json"
GATE_HISTORY_REL = "docs/mygamestudio/records/gate-history.md"


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _write(path: Path, text: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read(path)
    if existing == text:
        return False
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return True


def _pending_root(root: Path) -> Path:
    return root / PENDING_REL


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def _status_path(root: Path) -> Path:
    return _pending_root(root) / STATUS_NAME


def _load_status(root: Path) -> dict:
    return _load_json(_status_path(root))


def _save_status(root: Path, payload: dict) -> None:
    _save_json(_status_path(root), payload)


def _field(text: str, key: str) -> str:
    match = re.search(rf"{re.escape(key)}\s*[:：]\s*([^\n]+)", text or "")
    return match.group(1).strip().rstrip("。") if match else ""


def _section(text: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\n+(.*?)(?=\n## |\Z)"
    match = re.search(pattern, text or "", re.S)
    return (match.group(1) or "").strip() if match else ""


def _title(text: str) -> str:
    for line in (text or "").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def ensure_spec_mark(body: str, identity: str, version: str, kind: str) -> str:
    """正文缺规格身份章时按身份/种类/版本补一章;已有则原样返回。"""

    if SPEC_MARK in (body or ""):
        return body
    lines = (body or "").splitlines()
    insert = f"{SPEC_MARK}{identity}。种类:{kind}。版本:{version}。"
    if lines and lines[0].startswith("# "):
        return "\n".join([lines[0], "", insert] + lines[1:])
    return insert + "\n\n" + (body or "")


def _convert_gate(root: Path, staging: Path) -> dict:
    bits = [
        "# gate 历史留存",
        "",
        "本文件保存旧运行保障配置与待恢复记录,不是新版权限。",
        "普通工作不经 mgs-gate,旧令牌与运行根不得当作开工授权。",
        "",
    ]
    config_text = _read(root / DEFAULT_CONFIG_REL)
    gate_lines = [line for line in config_text.splitlines()
                  if "mgs-gate" in line or "运行保障" in line or "令牌" in line]
    if gate_lines:
        bits += ["## 旧 CONFIG 摘录", ""] + [
            f"- {line.lstrip('- ')}" for line in gate_lines] + [""]
    policy = _read(root / "docs/mygamestudio/records/gate-policy.md")
    if policy:
        bits += ["## 旧 gate 策略原文", "", policy.strip(), ""]
    recovery = _read(root / "docs/mygamestudio/records/recovery/pending-ops.json")
    if recovery:
        bits += ["## 待恢复记录", "", "```json", recovery.strip(), "```", ""]
    text = "\n".join(bits).rstrip() + "\n"
    wrote = _write(staging / GATE_HISTORY_REL, text)
    return {"kind": "gate-history", "new": GATE_HISTORY_REL, "wrote": wrote,
            "text": text}
