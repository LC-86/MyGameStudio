#!/usr/bin/env python3
"""Summarize local technical delivery evidence for a MyGameStudio package.

Public seams used at release-check time: summarize_technical_delivery and
write_technical_delivery. This does not publish, tag, push, or install.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import tarfile
from pathlib import Path

from mgs_upstream_upgrade import read_upstream_adoption

ADOPTED_UPSTREAM = {
    "name": "mattpocock/skills",
    "version": "1.2.3",
    "sha": "3cca18b368ae95cdbdebbff572ccafa662551015",
    "license": "MIT",
}
UNEXECUTED_RELEASE = (
    ("publish", "按既有有效授权发布（git push、PR、正式版本标签、插件发布）"),
    ("install-real-client", "安装到真实客户端 / 用户日常技能目录"),
    ("new-session-verification", "安装后用新会话核验发现、同名来源、调用与资料加载"),
    ("live-migration", "真实个人项目迁移"),
    ("live-switch", "用户环境切换 / 真实技能来源切换"),
)
NOT_SCHEDULED = (
    ("plugin-experience-signoff", "插件体验签收"),
    ("efficiency-comparison", "效率对照"),
)
MATT_USER_ONLY = (
    "ask-matt",
    "grill-me",
    "grill-with-docs",
    "handoff",
    "implement",
    "improve-codebase-architecture",
    "setup-matt-pocock-skills",
    "teach",
    "to-questionnaire",
    "to-spec",
    "to-tickets",
    "triage",
    "wait-what",
    "wayfinder",
)
# 承诺的完整公开技能集合(Matt 正式 25 项 + game-producer/game-init/
# game-design 三个游戏入口)。包/清单被从残缺目录重建时,只查
# 「非空且不重名」发现不了缺项;发现面必须与固定期望逐一对账。
EXPECTED_PUBLIC_SKILLS = (
    "ask-matt",
    "code-review",
    "codebase-design",
    "diagnosing-bugs",
    "domain-modeling",
    "game-design",
    "game-init",
    "game-producer",
    "grill-me",
    "grill-with-docs",
    "grilling",
    "handoff",
    "implement",
    "improve-codebase-architecture",
    "prototype",
    "research",
    "resolving-merge-conflicts",
    "setup-matt-pocock-skills",
    "tdd",
    "teach",
    "to-questionnaire",
    "to-spec",
    "to-tickets",
    "triage",
    "wait-what",
    "wayfinder",
    "wizard",
    "writing-for-agents",
)


def _root(path: Path | str) -> Path:
    return Path(path).resolve()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _plugin_files(plugin: Path) -> list[str]:
    return sorted(
        str(path.relative_to(plugin))
        for path in plugin.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
        and path.name != ".DS_Store"
    )


def _public_skills(plugin: Path) -> list[str]:
    root = plugin / "skills"
    if not root.is_dir():
        return []
    return sorted(
        path.name for path in root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def _parse_bullets(text: str, heading: str) -> list[str]:
    names: list[str] = []
    collecting = False
    for line in text.splitlines():
        if line.startswith("## "):
            collecting = line[3:].strip() == heading
            continue
        if collecting and line.startswith("- "):
            names.append(line[2:].strip())
    return names


def _status_rows(items: tuple[tuple[str, str], ...], *, status: str) -> list[dict]:
    return [
        {"item": item, "status": status, "reason": reason}
        for item, reason in items
    ]


def _package_consistency(plugin: Path, dist: Path, name: str, version: str) -> dict:
    tarball = dist / f"{name}-{version}.tar.gz"
    sums = dist / "SHA256SUMS.txt"
    manifest = dist / "package-manifest.txt"
    result = {
        "passed": False,
        "tarball": tarball.name if tarball.is_file() else "",
        "tarball_sha256": _sha256(tarball) if tarball.is_file() else "",
        "missing": [],
        "mismatches": [],
    }
    if not tarball.is_file():
        result["missing"].append(tarball.name)
    if not sums.is_file():
        result["missing"].append("SHA256SUMS.txt")
    if not manifest.is_file():
        result["missing"].append("package-manifest.txt")
    if result["missing"]:
        return result

    listed: dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, filename = parts[0], parts[1].strip().lstrip("*")
        listed[filename] = digest
        target = dist / filename
        if not target.is_file():
            result["mismatches"].append(f"missing:{filename}")
        elif _sha256(target) != digest:
            result["mismatches"].append(f"checksum:{filename}")
    if tarball.name not in listed:
        result["mismatches"].append("sums-missing-tarball")
    if "package-manifest.txt" not in listed:
        result["mismatches"].append("sums-missing-manifest")

    entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        entries[parts[1].strip().lstrip("*")] = parts[0].strip()
    plugin_files = _plugin_files(plugin)
    bundled_root = {"LICENSE", "THIRD_PARTY_NOTICES.md"}
    extra = set(entries) - set(plugin_files)
    missing = set(plugin_files) - set(entries)
    if missing or extra - bundled_root:
        result["mismatches"].append("manifest-set")
    for rel, digest in entries.items():
        path = (plugin.parent / rel) if rel in bundled_root else plugin / rel
        if path.is_file() and _sha256(path) != digest:
            result["mismatches"].append(f"manifest-hash:{rel}")
        elif not path.is_file():
            result["mismatches"].append(f"manifest-hash:{rel}")

    with tarfile.open(tarball, "r:gz") as tar:
        members = [
            member for member in tar.getmembers()
            if member.name.startswith("plugin/") and member.isfile()
        ]
        names = [member.name[len("plugin/"):] for member in members]
        extra_names = set(names) - set(plugin_files)
        missing_names = set(plugin_files) - set(names)
        if missing_names or extra_names - bundled_root:
            result["mismatches"].append("tarball-set")
        for member in members:
            rel = member.name[len("plugin/"):]
            source = (plugin.parent / rel) if rel in bundled_root else plugin / rel
            extracted = tar.extractfile(member)
            if extracted is None:
                result["mismatches"].append(f"tarball-hash:{rel}")
                continue
            archived = extracted.read()
            extracted.close()
            if not source.is_file() or source.read_bytes() != archived:
                result["mismatches"].append(f"tarball-hash:{rel}")
    result["passed"] = not result["mismatches"]
    return result


def _discovery(plugin: Path) -> dict:
    skills = _public_skills(plugin)
    contract = plugin / "internal" / "game" / "invocation.md"
    forbidden: list[str] = []
    if contract.is_file():
        forbidden = _parse_bullets(
            contract.read_text(encoding="utf-8"), "Must not auto-invoke")
    unique = len(skills) == len(set(skills))
    user_only_ok = sorted(forbidden) == sorted(MATT_USER_ONLY)
    expected = sorted(EXPECTED_PUBLIC_SKILLS)
    missing_skills = sorted(set(expected) - set(skills))
    unexpected_skills = sorted(set(skills) - set(expected))
    expected_ok = not missing_skills and not unexpected_skills
    local_ok = (bool(skills) and unique and contract.is_file() and user_only_ok
                and expected_ok)
    return {
        "public_skills": skills,
        "unique_names": unique,
        "user_only_not_auto_invoked": user_only_ok,
        "expected_skills_match": expected_ok,
        "missing_skills": missing_skills,
        "unexpected_skills": unexpected_skills,
        "local_package_surface": "passed" if local_ok else "failed",
        "install_session": "not-executed",
    }


def _pending_review_summary(captured: dict | None) -> dict:
    if not captured:
        return {
            "complete": False,
            "committed_only_complete": False,
            "created_commit": False,
            "excluded_unrelated": False,
            "axes_share_content_version": False,
            "content_version": "",
            "present": False,
        }
    axes = captured.get("axes") or {}
    version = captured.get("content_version") or ""
    standards = (axes.get("standards") or {}).get("content_version")
    spec = (axes.get("spec") or {}).get("content_version")
    excluded = captured.get("excluded") or []
    excluded_unrelated = any(
        ".scratch/" in str(item).replace("\\", "/") or str(item).endswith(".scratch")
        for item in excluded
    ) or bool(captured.get("target_scope", {}).get("exclude"))
    return {
        "present": True,
        "complete": bool(captured.get("complete")),
        "committed_only_complete": bool(captured.get("committed_only_complete")),
        "created_commit": bool(captured.get("created_commit")),
        "excluded_unrelated": bool(excluded_unrelated),
        "axes_share_content_version": (
            bool(version) and standards == version and spec == version
        ),
        "content_version": version,
        "baseline": captured.get("baseline") or "",
        "gate_required": bool(captured.get("gate_required")),
    }


def gather_environment(extra: dict | None = None) -> dict:
    uname = platform.uname()
    machine = {
        "system": f"{uname.system} {uname.release} {uname.machine}",
        "python": sys.version.split()[0],
        "check_client": "local-python-tests",
    }
    if extra:
        machine.update({key: value for key, value in extra.items() if value})
    return machine


def summarize_technical_delivery(
    repo_root: Path | str,
    *,
    plugin_root: Path | str | None = None,
    dist_root: Path | str | None = None,
    environment: dict | None = None,
    pending_review: dict | None = None,
) -> dict:
    """Build a reviewable local technical evidence pack. Does not publish."""

    repo = _root(repo_root)
    plugin = _root(plugin_root or (repo / "plugin"))
    dist = _root(dist_root or (repo / "dist"))
    manifest = _load_json(plugin / ".codex-plugin" / "plugin.json")
    name = manifest.get("name") or "mygamestudio"
    version = manifest.get("version") or ""
    adoption = read_upstream_adoption(plugin)
    env = gather_environment(environment)
    env["package_version"] = version
    consistency = _package_consistency(plugin, dist, name, version)
    discovery = _discovery(plugin)
    review = _pending_review_summary(pending_review)
    provenance_ok = (
        adoption.get("version") == ADOPTED_UPSTREAM["version"]
        and adoption.get("sha") == ADOPTED_UPSTREAM["sha"]
        and adoption.get("license") == ADOPTED_UPSTREAM["license"]
    )
    not_executed = _status_rows(UNEXECUTED_RELEASE, status="not-executed")
    not_executed.extend(_status_rows(NOT_SCHEDULED, status="not-scheduled"))
    local_ok = (
        consistency.get("passed") is True
        and provenance_ok
        and discovery.get("local_package_surface") == "passed"
        and (not review.get("present") or (
            review.get("complete") is True
            and review.get("committed_only_complete") is False
            and review.get("created_commit") is False
            and review.get("axes_share_content_version") is True
        ))
    )
    false_pass = [
        row["item"] for row in not_executed
        if row.get("status") in {"passed", "通过", True, "true"}
    ]
    acceptance = {
        "technical_behavior_evidence": "passed" if local_ok else "failed",
        "standards_spec_pending_review": (
            "passed" if review.get("present") and review.get("complete") else "incomplete"
        ),
        "package_consistency": "passed" if consistency.get("passed") else "failed",
        "versions_recorded": "passed" if env.get("system") and env.get("check_client") else "failed",
        "publish": "not-executed",
        "install-real-client": "not-executed",
        "new-session-verification": "not-executed",
        "live-migration": "not-executed",
        "live-switch": "not-executed",
        "plugin-experience-signoff": "not-scheduled",
        "efficiency-comparison": "not-scheduled",
    }
    tarball = dist / f"{name}-{version}.tar.gz"
    behaviors = [
        {"check": "T1", "status": "passed" if consistency.get("passed") and provenance_ok else "failed",
         "scope": "local-package"},
        {"check": "T2", "status": (
            "local-passed" if discovery.get("local_package_surface") == "passed" else "failed"
        ), "install_session": "not-executed"},
        {"check": "T3", "status": "evidenced-by-prior-ticket", "ticket": 53},
        {"check": "T4", "status": "evidenced-by-prior-ticket", "ticket": 51},
        {"check": "T5", "status": "evidenced-by-prior-ticket", "ticket": 53},
        {"check": "T6", "status": "evidenced-by-prior-ticket", "ticket": 54},
        {"check": "T7", "status": "evidenced-by-prior-ticket", "ticket": 54},
        {"check": "T8", "status": (
            "passed" if review.get("present") and review.get("complete")
            and review.get("axes_share_content_version")
            and review.get("committed_only_complete") is False else "incomplete"
        )},
        {"check": "T9", "status": "evidenced-by-prior-ticket", "ticket": 56},
        {"check": "T10", "status": "evidenced-by-prior-ticket", "ticket": 61},
        {"check": "T11", "status": "contract-evidenced",
         "live_migration": "not-executed"},
        {"check": "T12", "status": "contract-evidenced",
         "live_switch": "not-executed"},
        {"check": "T13", "status": "evidenced-by-prior-ticket", "ticket": 60},
        {"check": "T14", "status": "local-recorded",
         "install_session": "not-executed"},
    ]
    return {
        "ok": bool(local_ok) and not false_pass,
        "package": {
            "name": name,
            "version": version,
            "tarball": tarball.name if tarball.is_file() else "",
            "sha256": _sha256(tarball) if tarball.is_file() else "",
        },
        "upstream": {
            "name": adoption.get("name") or ADOPTED_UPSTREAM["name"],
            "version": adoption.get("version") or "",
            "sha": adoption.get("sha") or "",
            "license": adoption.get("license") or "",
            "decision": "retain",
            "new_candidate_authorized": False,
            "retain_reason": "no-new-candidate-authorized",
        },
        "environment": env,
        "package_consistency": consistency,
        "provenance": {"passed": provenance_ok},
        "discovery": discovery,
        "pending_review": review,
        "technical_behaviors": behaviors,
        "acceptance": acceptance,
        "not_executed": not_executed,
        "false_pass": false_pass,
    }


def _handover_markdown(evidence: dict) -> str:
    package = evidence.get("package") or {}
    upstream = evidence.get("upstream") or {}
    env = evidence.get("environment") or {}
    review = evidence.get("pending_review") or {}
    lines = [
        f"# MyGameStudio {package.get('version')} 技术检查交接（issue #62）",
        "",
        "本文件只记录本会话已完成本地技术检查与未执行交接。",
        "发布、真实安装、新会话核验仍等待额外授权，不能当成已经通过。",
        "",
        "## 已完成本地核对",
        "",
        f"- 包：`{package.get('name')} {package.get('version')}`，安装包 `{package.get('tarball')}`，SHA-256 `{package.get('sha256')}`",
        f"- 上游采用：{upstream.get('name')} {upstream.get('version')} `{upstream.get('sha')}`，许可 {upstream.get('license')}；无新候选，决定 retain",
        f"- 检查环境：系统 `{env.get('system')}`，Python `{env.get('python')}`，检查客户端 `{env.get('check_client')}`，客户端探测 `{env.get('client_probe') or '未探测'}`",
        f"- 包一致性：{((evidence.get('package_consistency') or {}).get('passed'))}",
        f"- 包内发现面与调用合同：{(evidence.get('discovery') or {}).get('local_package_surface')}",
        f"- 完整待审捕获 content_version：`{review.get('content_version') or '（写入时补齐）'}`",
        "",
        "## 未执行（等待额外授权，不标通过）",
        "",
    ]
    for row in evidence.get("not_executed") or []:
        lines.append(f"- `{row.get('item')}`：{row.get('status')} — {row.get('reason')}")
    lines.extend([
        "",
        "## 后续授权发布/安装时需要的合同与路径",
        "",
        f"- 安装包：`dist/{package.get('tarball')}`，校验 `dist/SHA256SUMS.txt`",
        "- 插件源：`plugin/`，清单 `plugin/.codex-plugin/plugin.json`（Codex）/ `plugin/.zcode-plugin/plugin.json`（ZCode）",
        "- 公开技能：`plugin/skills/*/SKILL.md`（Matt 正式 25 项 + game-producer/game-init/game-design）",
        "- 调用合同：`plugin/internal/game/invocation.md`",
        "- 阶段资料：`plugin/internal/game/stage-requirements.md`",
        "- 来源：`plugin/provenance/manifest.md`、`plugin/provenance/fingerprints.json`",
        "- 上游评估：`plugin/provenance/mgs_upstream_upgrade.py` 的 `evaluate_upstream_upgrade` / `apply_upstream_upgrade` / `read_upstream_adoption`",
        "- 完整待审：`plugin/internal/review/pending_review.py capture`",
        "- 记录接缝：`plugin/records/mgs_records.py`",
        "- 真实安装后核验：新会话发现 28 个技能、同名唯一、用户专用入口不被自动串调、资料读取不启动制作",
        "- 迁移/切换：仅在项目核对完成后使用 `plan_safe_switch` / `apply_safe_switch`；`real_migration_authorized` 仍为 false 时不得切换真实环境",
        "",
    ])
    return "\n".join(lines)


def write_technical_delivery(
    repo_root: Path | str,
    evidence: dict | None = None,
    **kwargs,
) -> dict:
    """Write dist evidence JSON and handover markdown. Does not publish."""

    repo = _root(repo_root)
    dist = _root(kwargs.get("dist_root") or (repo / "dist"))
    dist.mkdir(parents=True, exist_ok=True)
    payload = evidence or summarize_technical_delivery(repo, **kwargs)
    json_path = dist / "issue-62-technical-evidence.json"
    md_path = dist / "issue-62-handover.md"
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(_handover_markdown(payload), encoding="utf-8")
    payload = dict(payload)
    payload["evidence_path"] = str(json_path.relative_to(repo)) if json_path.is_relative_to(repo) else str(json_path)
    payload["handover_path"] = str(md_path.relative_to(repo)) if md_path.is_relative_to(repo) else str(md_path)
    return payload


if __name__ == "__main__":
    raise SystemExit(
        "mgs_release_check writes evidence only via write_technical_delivery(); "
        "do not run this module as a script."
    )
