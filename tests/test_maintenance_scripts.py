"""维护脚本与文档事实的回归检查。

运行：python3.12 -m pytest tests/test_maintenance_scripts.py -q

这些断言逐条对应合并前审查发现的问题，防止同类缺陷再次进入发布内容：
不可守卫的递归删除、绑定单机缓存路径、将 CLI 的技能筛选误当作 Git 引用、
以及把宿主属性写成通用事实。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
DOCS = REPO / "docs"
SKILLS = REPO / "skills"

SHELL_SCRIPTS = sorted(SCRIPTS.glob("*.sh"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    return [line for line in out if line.strip() and (REPO / line).is_file()]


@pytest.mark.parametrize("script", SHELL_SCRIPTS, ids=lambda p: p.name)
def test_shell_scripts_parse(script: Path) -> None:
    result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, f"{script.name} 语法错误：{result.stderr}"


def test_no_unguarded_recursive_delete_of_caller_supplied_path() -> None:
    """脚本不得对调用者传入的目录根做无条件 rm -rf。"""
    offenders = []
    for script in SHELL_SCRIPTS:
        text = read(script)
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.search(r"rm\s+-[rf]*\s+\"?\$(\{)?(OUT|TARGET|DEST|DIR|1)\b", stripped):
                offenders.append(f"{script.name}:{line_no}: {stripped}")
    assert not offenders, "存在对调用者目录的递归删除：\n" + "\n".join(offenders)


def test_fixture_script_refuses_non_empty_target_and_checks_cli_first() -> None:
    """夹具脚本必须先校验依赖与目标，再创建任何东西。"""
    text = read(SCRIPTS / "behavior-fixtures.sh")
    for marker in ("已存在且非空", "本脚本不会删除已有内容"):
        assert marker in text, f"缺少对非空输出目录的拒绝说明：{marker}"
    mkdir_at = text.find('mkdir -p "$OUT"')
    assert mkdir_at > 0, "夹具脚本应显式创建输出目录"
    for guard in ("resolve_skills_cli", "已存在且非空", "场景名不合法"):
        assert 0 <= text.find(guard) < mkdir_at, f"{guard} 必须发生在任何写入之前"
    # 参数校验不应依赖外部工具，也不该在检查阶段创建目录
    assert text.find("场景名不合法") < text.find("resolve_skills_cli"), \
        "场景名校验应先于 CLI 解析，使拒绝路径不依赖网络或缓存"
    assert 'OUT_PARENT="$(mkdir -p' not in text, "路径规范化阶段不得创建目录"


# --- 实际行为测试：真的跑脚本，而不是只查脚本里有没有提示文字 -------------

FIXTURE = SCRIPTS / "behavior-fixtures.sh"


def run_fixture(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    # 在现有环境上叠加，不整体替换：脚本需要 PATH、HOME 才能找到 node 与 git
    full_env = {**os.environ, "DO_NOT_TRACK": "1", "DISABLE_TELEMETRY": "1",
                **(env or {})}
    return subprocess.run(["bash", str(FIXTURE), *args],
                          capture_output=True, text=True, env=full_env, check=False)


def test_fixture_rejects_scenario_name_escaping_output_root(tmp_path: Path) -> None:
    """场景名 `../victim` 不得逃出输出根并覆盖既有工程。"""
    out = tmp_path / "out"
    victim = tmp_path / "victim"
    (victim / "project").mkdir(parents=True)
    sentinel = victim / "project" / "AGENTS.md"
    sentinel.write_text("SENTINEL-DO-NOT-TOUCH\n", encoding="utf-8")
    out.mkdir()

    result = run_fixture(str(out), "../victim")

    assert result.returncode != 0, f"越界场景名必须被拒绝，实际退出码 0：{result.stdout}"
    assert sentinel.read_text(encoding="utf-8") == "SENTINEL-DO-NOT-TOUCH\n", \
        "越界写入覆盖了既有文件"
    assert not (victim / "project" / "src").exists(), "越界写入创建了预期外的目录"
    assert not (victim / "project" / ".git").exists(), "越界写入在受害者目录里初始化了 git"
    assert list(out.iterdir()) == [], "输出根应保持为空"


def test_fixture_rejects_non_empty_output_and_preserves_content(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    keep = out / "previous-evidence.md"
    keep.write_text("已有验证证据\n", encoding="utf-8")

    result = run_fixture(str(out))

    assert result.returncode != 0, "非空输出目录必须被拒绝"
    assert keep.read_text(encoding="utf-8") == "已有验证证据\n", "脚本不得删除已有内容"


def test_fixture_rejects_protected_targets(tmp_path: Path) -> None:
    """受保护路径必须被拒；用临时 HOME 测，避免守卫失效时真的写入用户主目录。"""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    for target, env in ((str(fake_home), {"HOME": str(fake_home)}), ("/", None)):
        result = run_fixture(target, env=env)
        assert result.returncode != 0, f"应拒绝把 {target} 当作输出目录"


def test_fixture_rejects_bad_scenario_names(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    for bad in ("..", ".", "a/b", "/etc", "..\\x", "-x", "a;b", "$(touch pwn)"):
        result = run_fixture(str(out), bad)
        assert result.returncode != 0, f"应拒绝场景名 {bad!r}"
    assert list(out.iterdir()) == [], "拒绝路径不得留下任何产物"


def test_ci_workflows_run_the_whole_test_suite() -> None:
    """CI 与发布检查必须收集整个 tests/，否则新增回归文件不会阻止发布。"""
    for rel in (".github/workflows/check.yml", ".github/workflows/release.yml"):
        text = read(REPO / rel)
        assert re.search(r"pytest\s+tests/\s+-q", text), f"{rel} 未运行完整 tests/ 目录"
        assert "test_skills_layout.py tests/test_docs_product.py" not in text, \
            f"{rel} 仍用显式文件列表，会漏掉新增测试文件"


def test_all_test_files_are_collected_by_default_entry() -> None:
    """默认入口必须收集到 tests/ 下的每个测试文件，防止文件被静默排除。"""
    listed = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--collect-only", "-p", "no:cacheprovider"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert listed.returncode == 0, f"收集失败：{listed.stdout[-800:]}{listed.stderr[-400:]}"
    collected = set(re.findall(r"tests/(test_[a-z_]+)\.py", listed.stdout))
    on_disk = {p.stem for p in (REPO / "tests").glob("test_*.py")}
    assert collected == on_disk, f"未被收集的测试文件：{sorted(on_disk - collected)}"


def test_fixture_pins_initial_branch_and_builds_real_conflict(tmp_path: Path) -> None:
    """夹具不得假定初始分支只能是 main/master；S08 必须真的建立合并冲突现场。

    需要官方 skills CLI 才能装技能副本，取不到时按未运行处理而不是假装通过。
    """
    if not _skills_cli_available():
        pytest.skip("未取得 skills CLI，夹具生成未运行")
    out = tmp_path / "fixtures"
    env = {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "init.defaultBranch",
        "GIT_CONFIG_VALUE_0": "trunk",
    }
    result = run_fixture(str(out), "S08-conflict", env=env)
    assert result.returncode == 0, f"trunk 默认分支下夹具应仍能生成：{result.stdout[-600:]}"

    project = out / "S08-conflict" / "project"
    branch = subprocess.run(["git", "-C", str(project), "symbolic-ref", "--short", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    assert branch == "main", f"夹具应显式固定初始分支，实际 {branch}"
    assert (project / ".git" / "MERGE_HEAD").exists(), "S08 应留下进行中的合并"
    conflicted = subprocess.run(["git", "-C", str(project), "diff", "--name-only",
                                 "--diff-filter=U"],
                                capture_output=True, text=True, check=True).stdout.split()
    assert set(conflicted) == {"docs/design/GDD.md", "src/game.js"}, \
        f"冲突现场不符：{conflicted}"


def _skills_cli_available() -> bool:
    probe = subprocess.run(
        ["bash", "-c",
         f'. "{SCRIPTS / "resolve-skills-cli.sh"}" && '
         'resolve_skills_cli "${SKILLS_CLI_VERSION:-1.7.0}"'],
        capture_output=True, text=True, check=False,
    )
    return probe.returncode == 0


def test_shell_variables_before_multibyte_text_are_braced() -> None:
    """`$VAR` 紧跟全角标点时，bash 会把多字节字符读进变量名，在 set -u 下直接崩。

    这类缺陷只在报错分支触发，正常路径跑不到，因此必须静态守住。
    """
    bare = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7f]")
    offenders = []
    for script in SHELL_SCRIPTS:
        for line_no, line in enumerate(read(script).splitlines(), 1):
            if bare.search(line):
                offenders.append(f"{script.name}:{line_no}: {line.strip()[:70]}")
    assert not offenders, "变量后紧跟非 ASCII 且未加花括号：\n" + "\n".join(offenders)


def test_fixture_rejects_dotdot_bypass_of_non_empty_guard(tmp_path: Path) -> None:
    """`missing/../victim` 不得绕过非空检查。

    规范化失败时若回退到原始字符串，`-e` 会因中间目录不存在而返回假，
    随后 mkdir -p 先建出 missing、再经 .. 落进已有的非空目录。
    """
    victim = tmp_path / "victim"
    target = victim / "S01-ask" / "project"
    target.mkdir(parents=True)
    sentinel = target / "AGENTS.md"
    sentinel.write_text("SENTINEL\n", encoding="utf-8")
    escaping = str(tmp_path / "missing" / ".." / "victim")

    result = run_fixture(escaping, "S01-ask")

    assert result.returncode != 0, "含 .. 的输出路径必须被拒绝，不能回退到未规范化字符串"
    assert sentinel.read_text(encoding="utf-8") == "SENTINEL\n", "既有文件被覆盖"
    assert not (tmp_path / "missing").exists(), "校验阶段不得创建任何目录"
    assert not (target / ".git").exists(), "不得在受害者目录里初始化 git"
    assert ".." in result.stderr, "应说明拒绝原因与 .. 有关"


def test_fixture_still_allows_missing_intermediates_without_dotdot(tmp_path: Path) -> None:
    """缺失中间目录且不含 .. 时，路径校验应放行（后续步骤才失败），不能误拒。"""
    nested = str(tmp_path / "a" / "b" / "c")
    result = run_fixture(nested, env={"SKILLS_CLI": str(tmp_path / "no-such-cli.mjs")})

    assert result.returncode != 0, "CLI 不可用时仍应失败"
    assert "上级引用" not in result.stderr and "无法安全规范化" not in result.stderr, \
        f"合法嵌套路径被误判为不安全：{result.stderr}"
    assert "SKILLS_CLI" in result.stderr, "应走到 CLI 解析那一步才失败"
    assert not (tmp_path / "a").exists(), "依赖校验前不得创建输出目录"


def test_fixture_refuses_unlistable_output_directory(tmp_path: Path) -> None:
    """目录可写但不可列出时，非空检查不得把「列不出来」当成「是空的」。

    拒绝发生在依赖校验之前，因此本测试不需要 skills CLI。
    """
    if os.geteuid() == 0:
        pytest.skip("root 可以列出任意目录，无法构造不可读场景")
    out = tmp_path / "out"
    target = out / "S01-ask" / "project"
    target.mkdir(parents=True)
    sentinel = target / "AGENTS.md"
    sentinel.write_text("SENTINEL\n", encoding="utf-8")
    original_mode = out.stat().st_mode & 0o777
    out.chmod(0o311)  # 可进入、可写入，但不能列出内容
    try:
        result = run_fixture(str(out), "S01-ask")
    finally:
        out.chmod(original_mode)

    assert result.returncode != 0, "无法枚举目录内容时必须拒绝，不能当成空目录放行"
    assert "无法列出输出目录内容" in result.stderr, f"应说明枚举失败：{result.stderr}"
    assert sentinel.read_text(encoding="utf-8") == "SENTINEL\n", "既有文件被覆盖"
    assert not (target / "src").exists(), "不得在受害者目录里写入夹具"
    assert not (target / ".git").exists(), "不得在受害者目录里初始化 git"


def test_guard_checks_do_not_swallow_command_failures() -> None:
    """安全守卫不得用 `2>/dev/null` 吞掉命令退出码后按空结果放行。"""
    offenders = []
    for script in SHELL_SCRIPTS:
        for line_no, line in enumerate(read(script).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # 形如 [ -n "$(cmd 2>/dev/null)" ]：命令失败时结果为空，判断被绕过
            if re.search(r'\[\s*-n\s+"\$\([^"]*2>/dev/null', line):
                offenders.append(f"{script.name}:{line_no}: {stripped[:70]}")
            # 守卫循环里用 `|| continue` 跳过解析失败的受保护路径
            if "forbidden" in line and "continue" in line:
                offenders.append(f"{script.name}:{line_no}: {stripped[:70]}")
    assert not offenders, "守卫条件吞掉了失败状态：\n" + "\n".join(offenders)


def test_no_machine_specific_npx_cache_hash_in_tracked_files() -> None:
    """缓存目录名是内容哈希，不绑定某台机器；只允许出现通配形式。"""
    pattern = re.compile(r"_npx/(?!\*)[0-9a-z]{6,}")
    offenders = []
    for rel in tracked_files():
        if not rel.endswith((".md", ".sh", ".py", ".yml", ".yaml", ".json")):
            continue
        text = read(REPO / rel)
        for line_no, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{rel}:{line_no}")
    assert not offenders, "含单机 npx 缓存哈希：\n" + "\n".join(offenders)


def test_both_scripts_share_the_cli_resolver() -> None:
    """CLI 取数方式只维护一处。"""
    resolver = SCRIPTS / "resolve-skills-cli.sh"
    assert resolver.is_file(), "缺少共享的 resolve-skills-cli.sh"
    text = read(resolver)
    assert "SKILLS_CLI_CMD" in text
    assert "return 4" in text, "取不到 CLI 时必须以非零返回失败，不静默继续"
    for name in ("install-smoke-test.sh", "behavior-fixtures.sh"):
        body = read(SCRIPTS / name)
        assert "resolve-skills-cli.sh" in body, f"{name} 未复用共享解析器"
        assert re.search(r"resolve_skills_cli\s+", body), f"{name} 未调用 resolve_skills_cli"


def test_docs_do_not_claim_at_suffix_is_the_git_ref() -> None:
    """`@` 是技能筛选，`#` 才是 Git 引用；文档不得把它当成引用断言。

    允许在明确标记为「已纠正」的句子里复述旧说法，因为验证记录需要留下
    曾经错在哪里；只有不带纠正标记的断言才算回归。
    """
    false_claims = (
        re.compile(r"owner/repo@<ref>[^。\n]*作为\s*git\s*引用", re.IGNORECASE),
        re.compile(r"@\s*后缀[^。\n]*会作为\s*git\s*引用", re.IGNORECASE),
    )
    refutation = ("原先", "是错的", "已证伪", "误读", "纠正", "有误", "不要")
    offenders = []
    for rel in tracked_files():
        if not rel.endswith(".md") or rel.startswith("docs/design/"):
            continue
        text = read(REPO / rel)
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(marker in line for marker in refutation):
                continue
            for pattern in false_claims:
                if pattern.search(line):
                    offenders.append(f"{rel}:{line_no}")
    assert not offenders, "仍把 @ 后缀写成 Git 引用：\n" + "\n".join(offenders)

    installation = read(DOCS / "installation.md")
    for marker in ("技能筛选", "默认分支", "#ref", "#v3.0.0"):
        assert marker in installation, f"installation.md 应说明 {marker}"
    assert "Found 39 skills" in installation, \
        "installation.md 应保留误装旧版本的实测证据"


def test_delegation_states_isolation_is_host_dependent() -> None:
    """派发是否隔离父历史是宿主属性，不能写成通用事实。"""
    text = read(SKILLS / "docs-gamestudio" / "references" / "delegation.md")
    assert "宿主属性" in text, "应说明隔离性是宿主属性而非派发动作本身"
    assert "fork_turns" in text, "应给出继承父历史的具体反例"
    assert "核实" in text and "披露" in text, "应要求核实宿主并按需披露限制"

    skill = read(SKILLS / "docs-gamestudio" / "SKILL.md")
    assert "派发是否隔离由宿主决定" in skill, \
        "完成标准一节里「藏后续步骤」的杠杆同样要限定宿主条件"


def test_no_other_skill_asserts_isolation_as_universal_fact() -> None:
    """其他技能提到独立上下文时必须带条件或披露分支。"""
    offenders = []
    for path in SKILLS.rglob("*.md"):
        text = read(path)
        for line_no, line in enumerate(text.splitlines(), 1):
            if "独立上下文" in line or "独立子代理" in line:
                if not any(k in line for k in ("不能", "无法", "不支持", "没有", "是否",
                                               "当前", "确实", "获得", "能力")):
                    offenders.append(f"{path.relative_to(REPO)}:{line_no}: {line.strip()}")
    assert not offenders, "无条件断言独立上下文：\n" + "\n".join(offenders)
