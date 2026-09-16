#!/usr/bin/env python3
"""Issue #69(#68 第 2/5/6 项,R11 非挡发版)safe-switch 加固回归。

- #69-1: 切换计划必须携带包树指纹;确认与执行之间包内容被替换时,
  不得按旧清单安装来源不明的技能包,必须失败闭合。
- #69-2: package_root 与客户端安装目录重叠时不得先删后拷自毁,
  包来源与用户技能必须原样保留。
- #69-3: peer 就绪检查必须使用注入的 transport/api-base,且必须先于
  远端标记变更与本地文件提升;否则 peer 检查失败会把项目留在
  「已提升、无切换状态」的半完成状态。

反向验证坑:check() 只记录不抛错,本文件全部经 apply_safe_switch 等
真实执行路径断言,并查 FAILURES 列表判定红绿。

    python3 -B tests/test_r11_switch_regressions.py
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "records"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from records_backend_support import make_checker, run_theme  # noqa: E402

import mgs_records  # noqa: E402

from test_github_material_migration import _write_old_github_project  # noqa: E402
from test_safe_switch import (  # noqa: E402
    _convert_local, _write_isolated_client, _write_old_local_project)

FAILURES, check = make_checker()

PLUGIN_SKILLS = REPO_ROOT / "plugin" / "skills"
TAMPER = "确认后被替换的包内容:不得进入客户端环境。"
API_BASE_ENV = "MGS_GH_API_BASE"
TOKEN_ENVS = ("MGS_GITHUB_TOKEN", "GH_TOKEN")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ready_local(tmp: Path) -> Path:
    root = _write_old_local_project(tmp / "ready-game")
    _convert_local(root)
    return root


def _snapshot_skills(home: Path) -> dict[str, str]:
    skills = home / "skills"
    found: dict[str, str] = {}
    for path in sorted(skills.iterdir()):
        marker = path / "SKILL.md"
        if path.is_dir() and marker.is_file():
            found[path.name] = marker.read_text(encoding="utf-8")
    return found


def test_plan_carries_package_fingerprint_and_blocks_swap() -> None:
    """#69-1: 计划记录包树指纹;确认后包内容被替换必须失败闭合。"""

    with tempfile.TemporaryDirectory() as tmp:
        ready = _ready_local(Path(tmp))
        old_design = (ready / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8")
        home = Path(tmp) / "isolated-codex"
        _write_isolated_client(home)
        package = Path(tmp) / "package-skills"
        shutil.copytree(PLUGIN_SKILLS, package)
        plan = mgs_records.plan_safe_switch(
            ready, client_home=home, package_root=package)
        check(plan.get("ready") is True, f"前置:应可切换:{plan.get('blockers')}")
        fingerprints = plan.get("package_fingerprints") or {}
        check(bool(fingerprints), "切换计划必须携带包树指纹")
        check(fingerprints.get("tdd/SKILL.md") == _sha(package / "tdd" / "SKILL.md"),
              "包树指纹必须逐文件对应包内实际内容")
        # check 与 run 之间:包内一个尚未安装的新入口被整体替换。
        target = package / "game-design" / "SKILL.md"
        original = target.read_text(encoding="utf-8")
        target.write_text(original + "\n" + TAMPER + "\n", encoding="utf-8")
        applied = mgs_records.apply_safe_switch(ready, plan, confirmed=True)
        check(applied.get("ok") is False,
              f"确认后包内容被替换不得切换:{applied}")
        check(applied.get("wrote") is False, "包内容被替换时不得写入")
        check("game-design/SKILL.md" in str(applied.get("changed_package_files") or []),
              f"必须指出被替换的包文件,实际 {applied.get('changed_package_files')}")
        installed = home / "skills" / "game-design" / "SKILL.md"
        check(not installed.is_file()
              or TAMPER not in installed.read_text(encoding="utf-8"),
              "被替换的包内容不得进入客户端环境")
        check((ready / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8") == old_design, "包被替换时现行规格不得被提升")
        check((ready / "docs/mygamestudio/records/pending-switch"
               / "switch-status.json").exists() is False,
              "包被替换时不得写切换状态")
        # 恢复包内容后,同一份已确认清单必须可以正常完成切换。
        target.write_text(original, encoding="utf-8")
        applied = mgs_records.apply_safe_switch(ready, plan, confirmed=True)
        check(applied.get("ok") is True, f"包恢复后应可切换:{applied}")
        live = mgs_records.read_current_design(ready)
        check("规格身份:overall" in (live.get("overall") or ""),
              "包恢复后切换应使新版成为现行来源")
        installed = home / "skills" / "game-design" / "SKILL.md"
        check(installed.is_file() and TAMPER not in installed.read_text(
            encoding="utf-8"), "恢复后的正常包内容应可安装")


def test_package_root_overlapping_install_dir_does_not_self_destruct() -> None:
    """#69-2: 包根与安装目录重叠时不得先删后拷自毁,技能必须原样保留。"""

    with tempfile.TemporaryDirectory() as tmp:
        ready = _ready_local(Path(tmp))
        home = Path(tmp) / "isolated-codex"
        _write_isolated_client(home)
        skills = home / "skills"
        originals = _snapshot_skills(home)
        check(bool(originals), "前置:客户端应有已安装技能")
        # 包根就是客户端安装目录本身:旧代码对该目录先 rmtree 再 copytree,
        # 会把唯一的技能副本连同包来源一起删掉后拷贝失败。
        plan = mgs_records.plan_safe_switch(
            ready, client_home=home, package_root=skills)
        check(plan.get("ready") is True, f"前置:应可切换:{plan.get('blockers')}")
        try:
            applied = mgs_records.apply_safe_switch(ready, plan, confirmed=True)
        except Exception as exc:  # 旧代码在此崩溃并留下被删空的技能目录
            applied = {"ok": False, "reason": f"切换过程异常:{exc}"}
        check(applied.get("ok") is True,
              f"包根与安装目录重叠时不得崩溃或自毁:{applied.get('reason')}")
        for name, text in originals.items():
            live = skills / name / "SKILL.md"
            check(live.is_file() and live.read_text(encoding="utf-8") == text,
                  f"重叠自毁不得破坏已安装技能 {name}")
        check(applied.get("client_complete") is True,
              f"内容已是包本身的技能应如实报告客户端完成:{applied}")


def _github_ready_with_peer(tmp: Path) -> tuple[Path, Path, object, str]:
    """就绪 GitHub 项目 + 共用替身远端的待切换 peer;返回 (ready, peer, fake, 旧peer现行规格)."""

    ready, fake = _write_old_github_project(tmp / "gh-ready")
    mgs_records.apply_github_material_migration(
        ready, mgs_records.plan_github_material_migration(
            ready, transport=fake),
        confirmed=True, transport=fake)
    # peer 与就绪项目共用同一替身远端:peer 的迁移成果只能经注入
    # 传输完整回读,peer 就绪判定因此依赖注入是否被透传。
    peer, _ = _write_old_github_project(tmp / "gh-peer")
    old_peer_design = (peer / "docs/mygamestudio/GAME_DESIGN.md"
                       ).read_text(encoding="utf-8")
    mgs_records.apply_github_material_migration(
        peer, mgs_records.plan_github_material_migration(
            peer, transport=fake),
        confirmed=True, transport=fake)
    report = mgs_records.read_github_material_migration(peer, transport=fake)
    check(report.get("complete") is True
          and report.get("status") == "pending-switch",
          f"前置:peer 应经注入传输回读为待切换:{report.get('missing')}")
    return ready, peer, fake, old_peer_design


def _poison_default_endpoint():
    """把「丢弃注入后才会用到的默认端点」指到必然拒绝的本地端口。

    返回还原函数;同时摘掉令牌环境变量,避免任何默认请求携带凭据。
    """

    saved = {name: os.environ.get(name)
             for name in (API_BASE_ENV,) + TOKEN_ENVS}

    def restore():
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    for name in TOKEN_ENVS:
        os.environ.pop(name, None)
    os.environ[API_BASE_ENV] = "http://127.0.0.1:1"
    return restore


def test_peer_check_uses_injected_transport() -> None:
    """#69-3a: peer 检查必须透传注入 transport,就绪 peer 不得误报。"""

    with tempfile.TemporaryDirectory() as tmp:
        ready, peer, fake, old_peer_design = _github_ready_with_peer(
            Path(tmp))
        plan = mgs_records.plan_safe_switch(ready, transport=fake,
                                            peer_projects=[peer])
        check(plan.get("ready") is True, f"前置:应可切换:{plan.get('blockers')}")
        restore = _poison_default_endpoint()
        try:
            # 丢弃注入的 transport 时,peer 检查按默认端点发真实请求,
            # 指到必然拒绝的本地端口使该缺陷确定性暴露。
            try:
                applied = mgs_records.apply_safe_switch(
                    ready, plan, confirmed=True, transport=fake)
            except Exception as exc:  # 旧代码:peer 检查在提升之后崩溃
                applied = {"ok": False,
                           "reason": f"切换过程异常:{type(exc).__name__}:{exc}"}
        finally:
            restore()
        check(applied.get("ok") is True,
              f"注入传输可达的 peer 不得导致切换失败或崩溃:{applied.get('reason')}")
        check(applied.get("unready_projects") == [],
              f"就绪的 peer 不得被误报为未就绪:{applied.get('unready_projects')}")
        check((ready / "docs/mygamestudio/records/pending-switch"
               / "switch-status.json").is_file(),
              "切换完成必须落盘状态;peer 检查不得晚于本地提升,"
              "把项目留在已提升无状态的半完成态")
        check((peer / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8") == old_peer_design,
            "peer 项目自身不得被连带切换")
        peer_status = mgs_records.read_safe_switch(peer, transport=fake)
        check(peer_status.get("status") == "pending-switch",
              f"peer 必须保持自身待切换状态,实际 {peer_status.get('status')}")


def test_peer_check_reads_before_any_marker_or_promotion() -> None:
    """#69-3b: peer 检查的远端回读必须先于任何标记 PATCH 与本地提升。

    给 peer 登记一个就绪项目不引用的专属任务 Issue:peer 检查若被排到
    标记变更之后(旧实现如此,且丢弃注入传输),该读取要么缺席、要么
    发生在提升之后,留下「已提升、无状态文件」的半完成切换。
    """

    with tempfile.TemporaryDirectory() as tmp:
        ready, fake = _write_old_github_project(Path(tmp) / "gh-ready")
        mgs_records.apply_github_material_migration(
            ready, mgs_records.plan_github_material_migration(
                ready, transport=fake),
            confirmed=True, transport=fake)
        # 登记在共用远端上的 peer 专属旧任务:只有 peer 的转换会引用它。
        fake.seed_issue("04-boss", "Boss 战斗")
        peer, _ = _write_old_github_project(Path(tmp) / "gh-peer")
        old_peer_design = (peer / "docs/mygamestudio/GAME_DESIGN.md"
                           ).read_text(encoding="utf-8")
        mgs_records.apply_github_material_migration(
            peer, mgs_records.plan_github_material_migration(
                peer, transport=fake),
            confirmed=True, transport=fake)
        peer_report = mgs_records.read_github_material_migration(
            peer, transport=fake)
        check(peer_report.get("complete") is True
              and peer_report.get("status") == "pending-switch",
              f"前置:peer 应经注入传输回读为待切换:{peer_report.get('missing')}")
        boss_new = next((int(row.get("new_issue"))
                         for row in (peer_report.get("correspondence") or {}
                                     ).get("tasks") or []
                         if row.get("identity") == "04-boss"
                         and isinstance(row.get("new_issue"), int)), None)
        check(boss_new is not None, "前置:peer 应有专属任务的转换 Issue")
        plan = mgs_records.plan_safe_switch(ready, transport=fake,
                                            peer_projects=[peer])
        check(plan.get("ready") is True, f"前置:应可切换:{plan.get('blockers')}")
        before = len(fake.calls)
        restore = _poison_default_endpoint()
        try:
            try:
                applied = mgs_records.apply_safe_switch(
                    ready, plan, confirmed=True, transport=fake)
            except Exception as exc:  # 旧代码:peer 检查在提升之后崩溃
                applied = {"ok": False,
                           "reason": f"切换过程异常:{type(exc).__name__}:{exc}"}
        finally:
            restore()
        check(applied.get("ok") is True,
              f"注入传输可达的 peer 不得导致切换失败或崩溃:{applied.get('reason')}")
        check(applied.get("unready_projects") == [],
              f"就绪的 peer 不得被误报为未就绪:{applied.get('unready_projects')}")
        check((ready / "docs/mygamestudio/records/pending-switch"
               / "switch-status.json").is_file(),
              "切换完成必须落盘状态;peer 检查不得晚于本地提升,"
              "把项目留在已提升无状态的半完成态")
        check((peer / "docs/mygamestudio/GAME_DESIGN.md").read_text(
            encoding="utf-8") == old_peer_design,
            "peer 项目自身不得被连带切换")
        peer_status = mgs_records.read_safe_switch(peer, transport=fake)
        check(peer_status.get("status") == "pending-switch",
              f"peer 必须保持自身待切换状态,实际 {peer_status.get('status')}")
        # 顺序观测:peer 专属 Issue 只会被 peer 就绪检查读取;该读取必须
        # 出现在任何标记 PATCH 之前。
        window = fake.calls[before:]
        first_boss = next(
            (i for i, call in enumerate(window)
             if call[0] == "GET" and f"/issues/{boss_new}" in str(call[1])), None)
        first_patch = next(
            (i for i, call in enumerate(window)
             if call[0] == "PATCH" and "/issues/" in str(call[1])), None)
        check(first_boss is not None,
              "peer 就绪检查必须经注入传输回读 peer 状态")
        if first_boss is not None and first_patch is not None:
            check(first_boss < first_patch,
                  f"peer 检查(首个 peer 读取在 {first_boss})必须先于"
                  f"标记变更(首个 PATCH 在 {first_patch})")


def main() -> int:
    return run_theme(
        "issue #69 safe-switch 加固(包树指纹/重叠自毁/peer 注入)",
        (
            test_plan_carries_package_fingerprint_and_blocks_swap,
            test_package_root_overlapping_install_dir_does_not_self_destruct,
            test_peer_check_uses_injected_transport,
            test_peer_check_reads_before_any_marker_or_promotion,
        ),
        FAILURES)


if __name__ == "__main__":
    raise SystemExit(main())
