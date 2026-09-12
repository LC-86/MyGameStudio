#!/usr/bin/env python3
"""票 13-16 与 18 的隔离验收注入夹具结构与终态对应。

任务票 10 从 tests/test_plugin_package.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。各主题文件可直接运行:

    python3 -B tests/test_package_fixtures_acceptance_b.py
"""

import re
import sys
from plugin_package_support import (REPO_ROOT, make_checker, run_theme, sha256)

FAILURES, check = make_checker()

def test_accept13_fixture() -> None:
    """任务票 13:独立审查验收夹具——承接票 10/12 真实交付物(06 海鸥 SVG
    与结果、11 构建产物与待验收记录),使待验收成果完整可审,不改样例本体。"""

    fixtures = REPO_ROOT / "acceptance" / "13-independent-deliverable-review" / "fixtures"
    for rel in (
        "README.md",
        "assets/gull-glide.svg",
        "assets/gull-dive.svg",
        "docs/mygamestudio/work/06-gull-sprite/task.md",
        "docs/mygamestudio/work/06-gull-sprite/results/2026-09-08.md",
        "docs/mygamestudio/work/11-playable-build/task.md",
        "docs/mygamestudio/work/11-playable-build/results/2026-09-08.md",
        "build/index.html",
        "build/main.js",
    ):
        check((fixtures / rel).is_file(), f"accept-13 夹具缺少 {rel}")
    # 06/11 任务记录为待验收态(审查对象,非开工对象)
    for task_id in ("06-gull-sprite", "11-playable-build"):
        task_md = (fixtures / "docs" / "mygamestudio" / "work" / task_id / "task.md")
        if task_md.is_file():
            text = task_md.read_text(encoding="utf-8")
            check(re.search(r"进度(:|：)待验收", text) is not None,
                  f"夹具 {task_id} 进度应为待验收(本票审查对象)")
    # 06 结果记录中登记的 SVG 哈希与实际文件一致(审查输入的版本指纹可信)
    results06 = (fixtures / "docs" / "mygamestudio" / "work" / "06-gull-sprite"
                 / "results" / "2026-09-08.md")
    if results06.is_file():
        text = results06.read_text(encoding="utf-8")
        for svg in ("gull-glide.svg", "gull-dive.svg"):
            svg_path = fixtures / "assets" / svg
            if svg_path.is_file():
                check(sha256(svg_path) in text,
                      f"夹具 06 结果记录应含 {svg} 的实际 SHA-256")
        check("独立审查" in text, "夹具 06 结果记录应声明独立审查尚未进行")
    # 11 结果记录登记的产物哈希与实际 build 文件一致
    results11 = (fixtures / "docs" / "mygamestudio" / "work" / "11-playable-build"
                 / "results" / "2026-09-08.md")
    if results11.is_file():
        text = results11.read_text(encoding="utf-8")
        for prod in ("index.html", "main.js"):
            prod_path = fixtures / "build" / prod
            if prod_path.is_file():
                check(sha256(prod_path) in text,
                      f"夹具 11 结果记录应含 build/{prod} 的实际 SHA-256")
    # 组装式导出=字节一致:build 产物应与持久夹具(票 09 交付后的 src)逐字节一致
    src_fixture = REPO_ROOT / "acceptance" / "10-visual-asset-delivery" / "fixtures" / "src"
    for prod in ("index.html", "main.js"):
        build_file = fixtures / "build" / prod
        src_file = src_fixture / prod
        if build_file.is_file() and src_file.is_file():
            check(build_file.read_bytes() == src_file.read_bytes(),
                  f"夹具 build/{prod} 应与票 10 夹具 src/{prod} 逐字节一致"
                  "(组装式导出,票 12 终态承接)")
    # 承接票 10/12 验收终态的文件与 .tmp 终态逐字节一致(本机有 .tmp 时核对)
    for arena_rel, rel in (
        (".tmp/accept-10/projects/tide-pool/assets/gull-glide.svg", "assets/gull-glide.svg"),
        (".tmp/accept-10/projects/tide-pool/assets/gull-dive.svg", "assets/gull-dive.svg"),
        (".tmp/accept-10/projects/tide-pool/docs/mygamestudio/work/06-gull-sprite/task.md",
         "docs/mygamestudio/work/06-gull-sprite/task.md"),
        (".tmp/accept-10/projects/tide-pool/docs/mygamestudio/work/06-gull-sprite/results/2026-09-08.md",
         "docs/mygamestudio/work/06-gull-sprite/results/2026-09-08.md"),
        (".tmp/accept-12/projects/tide-pool/docs/mygamestudio/work/11-playable-build/task.md",
         "docs/mygamestudio/work/11-playable-build/task.md"),
        (".tmp/accept-12/projects/tide-pool/docs/mygamestudio/work/11-playable-build/results/2026-09-08.md",
         "docs/mygamestudio/work/11-playable-build/results/2026-09-08.md"),
        (".tmp/accept-12/projects/tide-pool/build/index.html", "build/index.html"),
        (".tmp/accept-12/projects/tide-pool/build/main.js", "build/main.js"),
    ):
        arena_file = REPO_ROOT / arena_rel
        if arena_file.is_file() and (fixtures / rel).is_file():
            check((fixtures / rel).read_bytes() == arena_file.read_bytes(),
                  f"accept-13 夹具 {rel} 应与验收终态逐字节一致")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("审查" in text, "夹具 README 当前请求应指向独立审查")
        check("待验收" in text, "夹具 README 应说明审查对象为待验收成果")
        for task_id in ("02-tide-timer", "06-gull-sprite", "10-warning-sfx",
                        "11-playable-build"):
            check(task_id in text, f"夹具 README 应引用待审任务 {task_id}")
    # 样例本体保持 v1 未动(既有票验收可复现;13 用夹具覆盖)
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(13 用夹具覆盖)")
def test_accept14_fixture() -> None:
    """任务票 14:试玩验收夹具——承接票 13 终态(evidence/ 5 份审查记录、02 修复
    说明、tide-extra.js 处置残留),叠加开发者试玩请求;不改样例本体。"""

    fixtures = REPO_ROOT / "acceptance" / "14-playtest-and-human-feedback" / "fixtures"
    for rel in (
        "README.md",
        "src/tide-extra.js",
        "docs/mygamestudio/work/02-tide-timer/results/2026-09-08-fix.md",
        "docs/mygamestudio/evidence/2026-09-08-review-02-tide-timer.md",
        "docs/mygamestudio/evidence/2026-09-08-review-06-gull-sprite.md",
        "docs/mygamestudio/evidence/2026-09-08-review-10-warning-sfx.md",
        "docs/mygamestudio/evidence/2026-09-08-review-11-playable-build.md",
        "docs/mygamestudio/evidence/2026-09-08-recheck-02-tide-timer.md",
    ):
        check((fixtures / rel).is_file(), f"accept-14 夹具缺少 {rel}")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("试玩" in text, "夹具 README 当前请求应指向试玩")
        check("11-playable-build" in text, "夹具 README 应引用试玩对象 11-playable-build")
        check("build/index.html" in text, "夹具 README 应给出运行入口 build/index.html")
        check("人工" in text, "夹具 README 应说明人工体验判断的参与约定")
        check("未收到" in text or "尚未收到" in text,
              "夹具 README 应声明当前未收到任何真实人工反馈")
        check("08-gull-playtest" in text,
              "夹具 README 应引用等待真实人工反馈的 08-gull-playtest")
    # 承接票 13 终态的文件与 .tmp 终态逐字节一致(本机有 .tmp 时核对)
    a13 = ".tmp/accept-13/projects/tide-pool"
    for rel in (
        "src/tide-extra.js",
        "docs/mygamestudio/work/02-tide-timer/results/2026-09-08-fix.md",
        "docs/mygamestudio/evidence/2026-09-08-review-02-tide-timer.md",
        "docs/mygamestudio/evidence/2026-09-08-review-06-gull-sprite.md",
        "docs/mygamestudio/evidence/2026-09-08-review-10-warning-sfx.md",
        "docs/mygamestudio/evidence/2026-09-08-review-11-playable-build.md",
        "docs/mygamestudio/evidence/2026-09-08-recheck-02-tide-timer.md",
    ):
        arena_file = REPO_ROOT / a13 / rel
        if arena_file.is_file() and (fixtures / rel).is_file():
            check((fixtures / rel).read_bytes() == arena_file.read_bytes(),
                  f"accept-14 夹具 {rel} 应与票 13 终态逐字节一致")
    # tide-extra.js 为票 13 的处置残留(解除引用且无副作用化),不再被入口引用
    entry = REPO_ROOT / "acceptance" / "10-visual-asset-delivery" / "fixtures" / "src" / "index.html"
    residue = fixtures / "src" / "tide-extra.js"
    if entry.is_file() and residue.is_file():
        check("tide-extra" not in entry.read_text(encoding="utf-8"),
              "入口 index.html 不应引用 tide-extra.js(票 13 修复后的状态)")
        check("已停用" in residue.read_text(encoding="utf-8"),
              "tide-extra.js 应为票 13 处置后的无副作用残留")
    # 样例本体保持 v1 未动(既有票验收可复现;14 用夹具覆盖)
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(14 用夹具覆盖)")
def test_accept15_fixture() -> None:
    """任务票 15:目标变化/并发/中断恢复验收夹具——在票 14 布景之上叠加
    开发者目标变化请求;承接的漂移事实在夹具栈中真实存在;不改样例本体。"""

    fixtures = REPO_ROOT / "acceptance" / "15-goal-change-concurrency-recovery" / "fixtures"
    check((fixtures / "README.md").is_file(), "accept-15 夹具缺少 README.md")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("目标变化" in text or "目标或范围变化" in text,
              "夹具 README 当前请求应为开发者目标变化请求")
        check("45" in text, "夹具 README 应给出具体变化(回合时长 45 秒)")
        check("追回" in text, "夹具 README 应触及追回窗口(可调参数化)")
    # 布景承接的漂移事实:14 层夹具的 04/05 仍引用 GAME_DESIGN v2(当前 v3)
    task05 = (REPO_ROOT / "acceptance" / "08-spec-to-local-tasks" / "fixtures"
              / "docs" / "mygamestudio" / "work" / "05-gull-swoop" / "task.md")
    if task05.is_file():
        check("GAME_DESIGN v2" in task05.read_text(encoding="utf-8"),
              "承接布景应保留 04/05 引用旧版本的真实漂移(票 09-14 遗留)")
    design14 = (REPO_ROOT / "acceptance" / "11-audio-asset-delivery" / "fixtures"
                / "docs" / "mygamestudio" / "GAME_DESIGN.md")
    if design14.is_file():
        check("基线版本:v3" in design14.read_text(encoding="utf-8"),
              "承接布景的 GAME_DESIGN 当前应为 v3(票 11 后)")
    # 样例本体保持 v1 未动
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(15 用夹具覆盖)")
def test_accept16_fixture() -> None:
    """任务票 16:制作统筹完整闭环验收夹具——承接票 15 终态(逐字节)+ 开发者
    闭环请求;漂移、待同步与待人工事实在夹具栈中真实存在;不改样例本体。"""

    fixtures = REPO_ROOT / "acceptance" / "16-producer-complete-loop" / "fixtures"
    check((fixtures / "README.md").is_file(), "accept-16 夹具缺少 README.md")
    readme = fixtures / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("闭环" in text, "夹具 README 当前请求应为完整小步闭环请求")
        check("50 秒" in text, "夹具 README 应包含开发者对 50 秒回会的确认决定")
        check("直接调用" in text or "直接专业调用" in text,
              "夹具 README 应声明直接专业调用(Game-Prototype)的事实")
        check("urgent-window" in text,
              "夹具 README 应引用直接调用的原型 urgent-window")
        check("讨论" in text, "夹具 README 应包含仅讨论请求(不进入制作)")
        check("PT-01" in text, "夹具 README 应引用 PT-01 缺陷修复交接")
        check("短规格" in text or "单项" in text,
              "夹具 README 应说明本轮以短规格/单项工作收口")
    # 承接票 15 终态的关键文件必须存在
    for rel in (
        "docs/mygamestudio/PROJECT.md",
        "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/records/decision-2026-09-08-round-45s.md",
        "docs/mygamestudio/work/12-game-design-v4/task.md",
        "docs/mygamestudio/work/15-race-demo/results/race.md",
        "docs/mygamestudio/work/02-tide-timer/task.md",
        "docs/mygamestudio/work/04-shell-combo/task.md",
        "docs/mygamestudio/work/05-gull-swoop/task.md",
        "docs/mygamestudio/work/06-gull-sprite/task.md",
        "docs/mygamestudio/work/08-gull-playtest/task.md",
        "docs/mygamestudio/work/10-warning-sfx/task.md",
        "docs/mygamestudio/work/11-playable-build/task.md",
    ):
        check((fixtures / rel).is_file(), f"accept-16 夹具缺少承接票 15 终态的 {rel}")
    # 承接事实的结构核对
    design = fixtures / "docs" / "mygamestudio" / "GAME_DESIGN.md"
    if design.is_file():
        text = design.read_text(encoding="utf-8")
        check("基线版本:v4" in text,
              "承接布景的 GAME_DESIGN 应为 v4(50 秒手工变更未同步版本号)")
        check("50 秒" in text, "承接布景的 GAME_DESIGN 应含开发者手工 50 秒变更")
    task04 = fixtures / "docs" / "mygamestudio" / "work" / "04-shell-combo" / "task.md"
    if task04.is_file():
        check("needs-triage" in task04.read_text(encoding="utf-8"),
              "承接布景的 04/05/08 应保持 needs-triage(待重核)")
    task12 = fixtures / "docs" / "mygamestudio" / "work" / "12-game-design-v4" / "task.md"
    if task12.is_file():
        text = task12.read_text(encoding="utf-8")
        check("待执行" in text,
              "承接布景的 12-game-design-v4 应为待执行(v4 已采纳但记录待统筹同步)")
    task02 = fixtures / "docs" / "mygamestudio" / "work" / "02-tide-timer" / "task.md"
    if task02.is_file():
        text = task02.read_text(encoding="utf-8")
        check("待验收" in text, "承接布景的 02 应保持待验收")
        check("evidence/" in text, "承接布景的 02 结果索引应已登记 evidence(票 15)")
        check("开发者注" in text or "开发者" in text,
              "承接布景的 02 应保留票 15 的开发者注(恢复不覆盖用户修改)")
    # 承接票 15 终态的文件与 .tmp 终态逐字节一致(本机有 .tmp 时核对)
    a15 = ".tmp/accept-15/projects/tide-pool"
    for rel in (
        "docs/mygamestudio/PROJECT.md",
        "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/records/decision-2026-09-08-round-45s.md",
        "docs/mygamestudio/work/12-game-design-v4/task.md",
        "docs/mygamestudio/work/15-race-demo/results/race.md",
        "docs/mygamestudio/work/02-tide-timer/task.md",
        "docs/mygamestudio/work/04-shell-combo/task.md",
        "docs/mygamestudio/work/05-gull-swoop/task.md",
        "docs/mygamestudio/work/06-gull-sprite/task.md",
        "docs/mygamestudio/work/08-gull-playtest/task.md",
        "docs/mygamestudio/work/10-warning-sfx/task.md",
        "docs/mygamestudio/work/11-playable-build/task.md",
    ):
        arena_file = REPO_ROOT / a15 / rel
        if arena_file.is_file() and (fixtures / rel).is_file():
            check((fixtures / rel).read_bytes() == arena_file.read_bytes(),
                  f"accept-16 夹具 {rel} 应与票 15 终态逐字节一致")
    # 样例本体保持 v1 未动
    sample_design = (REPO_ROOT / "samples" / "tide-pool" / "docs" / "mygamestudio"
                     / "GAME_DESIGN.md")
    if sample_design.is_file():
        check("基线版本:v1" in sample_design.read_text(encoding="utf-8"),
              "samples/tide-pool 本体应保持 v1(16 用夹具覆盖)")
def test_accept18_fixture() -> None:
    """任务票 18:P 环夹具 atlas-drop(已有项目,本地后端)结构与承接事实。"""

    fixtures = REPO_ROOT / "acceptance" / "18-complete-package-acceptance" / "fixtures" / "atlas-drop"
    if not fixtures.is_dir():
        check(False, "缺少 acceptance/18 夹具 atlas-drop/")
        return
    for rel in (
        "README.md",
        "src/main.js",
        "docs/mygamestudio/INDEX.md",
        "docs/mygamestudio/CONFIG.md",
        "docs/mygamestudio/PROJECT.md",
        "docs/mygamestudio/GAME_DESIGN.md",
        "docs/mygamestudio/TECH_DESIGN.md",
        "docs/mygamestudio/work/01-shield-pickup/task.md",
        "docs/mygamestudio/work/02-speed-tune/task.md",
    ):
        check((fixtures / rel).is_file(), f"atlas-drop 夹具缺少 {rel}")
    config = (fixtures / "docs/mygamestudio/CONFIG.md")
    if config.is_file():
        text = config.read_text()
        check("- 后端:local-markdown" in text, "atlas-drop CONFIG 应为 local-markdown 后端")
        check("外部连接引用及已确认操作范围:无" in text, "atlas-drop CONFIG 应无外部授权")
    project = fixtures / "docs/mygamestudio/PROJECT.md"
    if project.is_file():
        check("基线版本:v1" in project.read_text(), "atlas-drop PROJECT 应为 v1(承接事实)")
    design = fixtures / "docs/mygamestudio/GAME_DESIGN.md"
    if design.is_file():
        check("基线版本:v1" in design.read_text(), "atlas-drop GAME_DESIGN 应为 v1(承接事实)")
    task01 = fixtures / "docs/mygamestudio/work/01-shield-pickup/task.md"
    task02 = fixtures / "docs/mygamestudio/work/02-speed-tune/task.md"
    if task01.is_file():
        text = task01.read_text()
        check("任务身份:01-shield-pickup" in text and "ready-for-agent" in text,
              "atlas-drop 任务 01 应为 ready-for-agent/待执行(承接事实)")
    if task02.is_file():
        text = task02.read_text()
        check("任务身份:02-speed-tune" in text and "needs-triage" in text,
              "atlas-drop 任务 02 应为 needs-triage(承接事实)")
        check("01-shield-pickup" in text, "atlas-drop 任务 02 应依赖 01(供 ready 解析)")


TESTS = (
    test_accept13_fixture,
    test_accept14_fixture,
    test_accept15_fixture,
    test_accept16_fixture,
    test_accept18_fixture,

)


def main() -> int:
    return run_theme("验收注入夹具(13-16/18)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())
