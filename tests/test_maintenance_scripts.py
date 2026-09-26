"""维护脚本与文档事实的回归检查。

运行：python3.12 -m pytest tests/test_maintenance_scripts.py -q

这些断言逐条对应合并前审查发现的问题，防止同类缺陷再次进入发布内容：
不可守卫的递归删除、绑定单机缓存路径、将 CLI 的技能筛选误当作 Git 引用、
以及把宿主属性写成通用事实。第三组守护（Issue #93）反过来断言已删除的维护脚本
与随包方法副本不再出现，避免这些路径被静默当成仍然可用。
"""

from __future__ import annotations

import os
import re
import shutil
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
    for guard in ("resolve_skills_cli", "已存在且非空", "场景名不合法", "METHOD_SOURCE 只支持"):
        assert 0 <= text.find(guard) < mkdir_at, f"{guard} 必须发生在任何写入之前"
    # 参数校验不应依赖外部工具，也不该在检查阶段创建目录
    assert text.find("场景名不合法") < text.find("resolve_skills_cli"), \
        "场景名校验应先于 CLI 解析，使拒绝路径不依赖网络或缓存"
    assert text.find("METHOD_SOURCE 只支持") < text.find("resolve_skills_cli"), \
        "METHOD_SOURCE 校验应先于 CLI 解析，使拒绝路径不依赖网络或缓存"
    assert 'OUT_PARENT="$(mkdir -p' not in text, "路径规范化阶段不得创建目录"


# --- 实际行为测试：真的跑脚本，而不是只查脚本里有没有提示文字 -------------

FIXTURE = SCRIPTS / "behavior-fixtures.sh"


def run_fixture(*args: str, env: dict[str, str] | None = None,
                cwd: Path | None = None) -> subprocess.CompletedProcess:
    # 在现有环境上叠加，不整体替换：脚本需要 PATH、HOME 才能找到 node 与 git
    full_env = {**os.environ, "DO_NOT_TRACK": "1", "DISABLE_TELEMETRY": "1",
                **(env or {})}
    return subprocess.run(["bash", str(FIXTURE), *args],
                          capture_output=True, text=True, env=full_env,
                          cwd=cwd, check=False)


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


def test_fixture_rejects_unknown_method_source_before_writing(tmp_path: Path) -> None:
    """METHOD_SOURCE 只认 official；写错时必须在创建任何东西、解析 CLI 之前失败。"""
    out = tmp_path / "out"
    result = run_fixture(str(out), "S01-ask",
                         env={"METHOD_SOURCE": "fork",
                              "SKILLS_CLI": str(tmp_path / "no-such-cli.mjs")})

    assert result.returncode != 0, "未知 METHOD_SOURCE 必须被拒绝"
    assert "METHOD_SOURCE" in result.stderr and "official" in result.stderr, \
        f"应指出 METHOD_SOURCE 只支持 official，实际 stderr：{result.stderr}"
    assert "SKILLS_CLI" not in result.stderr, \
        f"参数校验必须发生在 CLI 解析之前，实际 stderr：{result.stderr}"
    assert not out.exists() or list(out.iterdir()) == [], \
        "拒绝路径不得创建输出目录或任何产物"


def test_fixture_rejects_bundled_method_source(tmp_path: Path) -> None:
    """随包副本退役后，`METHOD_SOURCE=bundled` 必须在写入与 CLI 解析之前被拒绝。

    这是执行出来的拒绝路径，不是 grep 脚本文本：用一个不存在的 SKILLS_CLI 证明
    失败发生在依赖解析之前，而不是「bundled 模式跑到后面某步才连带失败」。
    """
    out = tmp_path / "out"
    result = run_fixture(str(out), "S01-ask",
                         env={"METHOD_SOURCE": "bundled",
                              "SKILLS_CLI": str(tmp_path / "no-such-cli.mjs")})

    assert result.returncode != 0, "bundled 已随副本退役，必须被拒绝"
    assert "METHOD_SOURCE" in result.stderr, \
        f"应由参数校验直接拒绝，实际 stderr：{result.stderr}"
    assert "SKILLS_CLI" not in result.stderr, \
        f"拒绝必须发生在 CLI 解析之前，实际 stderr：{result.stderr}"
    assert not out.exists() or list(out.iterdir()) == [], \
        "拒绝路径不得创建输出目录或任何产物"


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

    需要官方 skills CLI 和官方共同方法仓库可达才能装技能副本；依赖不可用时
    按未运行处理，而不是把外部网络故障报告成夹具行为失败。
    """
    if not _fixture_dependencies_available():
        pytest.skip("未取得 skills CLI 或官方共同方法仓库不可达，夹具生成未运行")
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


def _fixture_dependencies_available() -> bool:
    probe = subprocess.run(
        ["bash", "-c",
         f'. "{SCRIPTS / "resolve-skills-cli.sh"}" && '
         'resolve_skills_cli "${SKILLS_CLI_VERSION:-1.7.0}"'],
        capture_output=True, text=True, check=False,
    )
    return probe.returncode == 0 and _official_method_source_available()


def _official_method_source_available() -> bool:
    """确认外部安装依赖可达，避免 CLI 已缓存但官方仓库离线时误报夹具失败。"""
    try:
        probe = subprocess.run(
            ["git", "ls-remote", "--exit-code", "https://github.com/mattpocock/skills.git", "HEAD"],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0 and bool(probe.stdout.strip())


@pytest.mark.parametrize("failure", [
    "unreachable",
    "timeout",
])
def test_official_method_source_probe_skips_unavailable_repo(monkeypatch, failure: str) -> None:
    def unavailable(command, **kwargs):
        assert command == ["git", "ls-remote", "--exit-code",
                           "https://github.com/mattpocock/skills.git", "HEAD"]
        assert kwargs["timeout"] == 10
        if failure == "timeout":
            raise subprocess.TimeoutExpired(cmd=command, timeout=10)
        return subprocess.CompletedProcess(command, returncode=128, stdout="", stderr="offline")

    monkeypatch.setattr(subprocess, "run", unavailable)

    assert not _official_method_source_available()


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


_MKDIR_WRAPPER = """#!/bin/bash
real=/bin/mkdir
if [ "${FAIL_PROJECT_MKDIR:-}" = "1" ]; then
  for arg in "$@"; do
    case "$arg" in
      -*) continue ;;
      */S01-ask/project|*/S01-ask/project/*) exit 73 ;;
    esac
  done
fi
"$real" "$@"
status=$?
if [ "$status" -ne 0 ]; then
  exit "$status"
fi
if [ "${LOCK_PROJECT_AFTER_TASK_MKDIR:-}" = "1" ]; then
  for arg in "$@"; do
    case "$arg" in
      */S01-ask/project/tasks/*)
        chmod 000 "${arg%/tasks/*}" || exit 99
        ;;
    esac
  done
fi
exit 0
"""

_FAKE_SKILLS_CLI = """\
// 夹具脚本现在按两来源安装：本仓库 20 项 + 官方外部共同方法，并核对装到的项数。
// 桩必须真的造出这两部分，否则夹具会在自己的项数校验处停下，故障注入用例就测不到
// mkdir / cd 这些目标路径。桩只复制真实技能目录，不联网、不解析夹具的返回值。
const fs = require('fs');
const path = require('path');
const args = process.argv.slice(2);
if (args.includes('--version')) process.exit(0);

// --skill 后面可以跟多个技能名，直到下一个以 - 开头的参数为止。
function skillsAfterFlag() {
  const out = [];
  let collecting = false;
  for (const arg of args) {
    if (collecting) {
      if (arg.startsWith('-')) break;
      out.push(arg);
    } else if (arg === '--skill') {
      collecting = true;
    }
  }
  return out;
}

function mergeLock(records) {
  const lockPath = path.join(process.cwd(), 'skills-lock.json');
  const lock = fs.existsSync(lockPath)
    ? JSON.parse(fs.readFileSync(lockPath, 'utf8'))
    : { skills: {} };
  for (const [name, record] of Object.entries(records)) {
    lock.skills[name] = record;
  }
  fs.writeFileSync(lockPath, JSON.stringify(lock, null, 2) + '\\n');
}

function samePath(a, b) {
  try {
    return fs.realpathSync(a) === fs.realpathSync(b);
  } catch (error) {
    return a === b;
  }
}

if (args[0] === 'add') {
  const target = args[1];
  const dest = path.join(process.cwd(), '.agents', 'skills');
  const names = skillsAfterFlag();
  const records = {};
  if (samePath(target, process.env.FAKE_SKILLS_REPO || '')) {
    for (const name of names) {
      fs.cpSync(path.join(target, 'skills', name), path.join(dest, name), { recursive: true });
      records[name] = { source: target, sourceType: 'github', computedHash: '0'.repeat(64) };
    }
  } else if (target === 'mattpocock/skills') {
    for (const name of names) {
      const dir = path.join(dest, name);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, 'SKILL.md'), '---\\nname: ' + name + '\\n---\\n');
      records[name] = { source: target, sourceType: 'github', computedHash: '1'.repeat(64) };
    }
  } else {
    process.stderr.write('unexpected add target: ' + target + '\\n');
    process.exit(2);
  }
  mergeLock(records);
  process.exit(0);
}
process.stderr.write('unexpected args: ' + args.join(' ') + '\\n');
process.exit(2);
"""


def _stub_fixture_env(tmp_path: Path, **extra: str) -> tuple[Path, dict[str, str]]:
    """桩 CLI 走到夹具生成，并把 mkdir 换成可注入失败的包装。不联网。"""
    if shutil.which("node") is None:
        pytest.skip("没有 node，无法用桩 CLI 走到夹具生成")
    caller = tmp_path / "caller"
    caller.mkdir()
    (caller / "AGENTS.md").write_text("SENTINEL-DO-NOT-TOUCH\n", encoding="utf-8")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    wrapper = bindir / "mkdir"
    wrapper.write_text(_MKDIR_WRAPPER, encoding="utf-8")
    wrapper.chmod(0o755)
    fake = tmp_path / "fake-skills-cli.js"
    fake.write_text(_FAKE_SKILLS_CLI, encoding="utf-8")
    env = {
        "PATH": str(bindir) + os.pathsep + os.environ.get("PATH", ""),
        "SKILLS_CLI": str(fake),
        "FAKE_SKILLS_REPO": str(REPO),
        **extra,
    }
    return caller, env


def _assert_caller_untouched(caller: Path) -> None:
    sentinel = caller / "AGENTS.md"
    assert sentinel.read_text(encoding="utf-8") == "SENTINEL-DO-NOT-TOUCH\n"
    assert {p.name for p in caller.iterdir()} == {"AGENTS.md"}
    assert not (caller / ".git").exists()
    assert not (caller / "CONTEXT.md").exists()


def test_fixture_project_mkdir_failure_does_not_write_caller_directory(tmp_path: Path) -> None:
    """项目目录创建失败时必须马上停，不能在调用者的当前目录继续 git 和相对路径写入。

    第五轮审查的故障注入：只让 `S01-ask/project` 及其子目录的 mkdir 返回 73，
    其余命令真实执行。`make_project || ...` 会关掉函数内的 set -e，于是 cd 失败后
    仍会在调用者目录里 git init，并覆盖那里的 AGENTS.md。
    """
    caller, env = _stub_fixture_env(tmp_path, FAIL_PROJECT_MKDIR="1")
    out = tmp_path / "out"
    result = run_fixture(str(out), "S01-ask", env=env, cwd=caller)

    assert result.returncode == 73, (
        f"应带回 mkdir 的退出码 73，实际 {result.returncode}\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    assert "无法创建项目目录" in result.stderr
    assert "git init" not in result.stderr
    assert "No such file or directory" not in result.stderr
    _assert_caller_untouched(caller)
    assert not (out / "S01-ask" / "project" / ".git").exists()


def test_fixture_project_cd_failure_does_not_write_caller_directory(tmp_path: Path) -> None:
    """目录已经建好但进不去时，也必须停在 cd，不能接着在调用者目录里写文件。"""
    if os.geteuid() == 0:
        pytest.skip("root 仍能进入 000 权限的目录，无法构造 cd 失败")
    caller, env = _stub_fixture_env(tmp_path, LOCK_PROJECT_AFTER_TASK_MKDIR="1")
    out = tmp_path / "out"
    project = out / "S01-ask" / "project"
    try:
        result = run_fixture(str(out), "S01-ask", env=env, cwd=caller)
    finally:
        if project.is_dir():
            os.chmod(project, 0o755)

    assert result.returncode != 0, f"进不了项目目录必须失败：{result.stderr}"
    assert "无法进入项目目录" in result.stderr, result.stderr
    assert "git init" not in result.stderr
    _assert_caller_untouched(caller)
    assert project.is_dir()
    assert not (project / ".git").exists()


def test_fixture_stub_cli_still_builds_project_without_touching_caller(tmp_path: Path) -> None:
    """失败路径收紧后，正常生成仍把仓库和文件写在夹具项目里，调用者目录保持原样。"""
    caller, env = _stub_fixture_env(tmp_path)
    out = tmp_path / "out"
    result = run_fixture(str(out), "S01-ask", env=env, cwd=caller)

    assert result.returncode == 0, f"桩 CLI 下夹具应生成成功：{result.stderr}\n{result.stdout}"
    _assert_caller_untouched(caller)
    project = out / "S01-ask" / "project"
    text = (project / "AGENTS.md").read_text(encoding="utf-8")
    assert text.startswith("## Agent 约定\n"), "夹具正文不应因写入方式改变"
    assert (project / "CONTEXT.md").is_file()
    head = subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=False)
    assert head.returncode == 0 and head.stdout.strip(), "夹具项目应有可用基线提交"


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


def test_two_source_composition_check_rejects_incomplete_installation(tmp_path: Path) -> None:
    """两来源组合校验由共享脚本提供，且必须自己发现装不齐的组合。

    `install-smoke-test.sh` 的第 10 节（#92 组）与第 11 节（#91 组）共用这一份检查。
    这里验证两件事：两节确实共用同一个脚本（避免再次各复制一份后漂移），以及该脚本
    在目录缺项、锁文件缺失时逐条报 FAIL 并非零退出，而不是只要跑起来就算通过。
    随包副本退役后签名里不再有 `--bundled`：该校验只核对官方来源与锁记录。
    """
    checker = SCRIPTS / "two-source-composition-check.py"
    assert checker.is_file(), "两来源组合校验应由 scripts/two-source-composition-check.py 提供"
    smoke = read(SCRIPTS / "install-smoke-test.sh")
    assert smoke.count("two-source-composition-check.py") == 2, \
        "第 10、11 节应共用同一份组合校验，而不是各写一份"

    dest = tmp_path / "skills"
    (dest / "ask-gamestudio").mkdir(parents=True)
    result = subprocess.run(
        ["python3.12", str(checker), "--lock", str(tmp_path / "missing-lock.json"),
         "--dest", str(dest),
         "--repo", str(REPO), "--label", "测试组", "--group", "ask-gamestudio"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0, "装不齐的组合不得判为通过"
    assert "FAIL" in result.stdout, result.stdout
    assert "PASS" not in result.stdout, "失败时不得同时给出通过结论"
    assert "组合安装目录不符" in result.stdout, result.stdout
    assert "没有生成 skills-lock.json" in result.stdout, result.stdout


def test_two_source_composition_check_no_longer_takes_a_bundled_copy() -> None:
    """随包副本退役后，组合校验不得再接受 `--bundled` 参数。

    参数还在就意味着校验仍在拿随包副本做对照；真跑一次参数解析能发现这件事，
    而看文档或看 --help 文本发现不了。
    """
    checker = SCRIPTS / "two-source-composition-check.py"
    result = subprocess.run(
        ["python3.12", str(checker), "--lock", str(SCRIPTS / "no-such-lock.json"),
         "--dest", str(SCRIPTS), "--bundled", str(SKILLS / "writing-for-agents"),
         "--repo", str(REPO), "--label", "测试组", "--group", "ask-gamestudio"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0, "--bundled 必须被拒绝，不再有随包副本可比对"
    assert "--bundled" in result.stderr, f"应指出未知参数：{result.stderr}"


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


def test_docs_do_not_claim_pinned_ref_still_unverified() -> None:
    """`#<ref>` 已用真实分支与标签各测一例，文档不得继续把它写成未验证。

    验证记录需要留下「曾经没跑通」的过程，因此同一行带此前/变成/已实测等
    复盘标记时放行；只有把未验证当成当前状态的断言才算回归。
    """
    ref_token = ("#<ref>", "`#v", "固定引用", "固定标签")
    not_verified = ("尚未端到端", "端到端未成功", "未端到端验证", "端到端未", "别写进脚本")
    retrospective = ("此前", "原先", "已实测", "已通过", "变成", "已用", "纠正", "关闭")
    offenders = []
    for rel in tracked_files():
        if not rel.endswith(".md") or rel.startswith("docs/design/"):
            continue
        for line_no, line in enumerate(read(REPO / rel).splitlines(), 1):
            if any(m in line for m in retrospective):
                continue
            if any(t in line for t in ref_token) and any(m in line for m in not_verified):
                offenders.append(f"{rel}:{line_no}")
    assert not offenders, "仍把 #<ref> 写成未端到端验证：\n" + "\n".join(offenders)


# 外部共同方法的 subagent-delegation.md 曾按随包副本断言；副本退役后不再从这里读取它，
# 本仓库自有的委派契约改由 test_skills_layout.py::test_delegation_contract_covers_brief_and_return_check
# 在 docs-gamestudio/references/delegation.md 上守住。
#
# --- Issue #93：已删除维护脚本的退役守护 ---------------------------------
# 来源矩阵、安装核验与同步生成器随随包副本一起退役。文件名用相邻字符串拼接构造：
# 直接写出完整名字时，本守卫自己的声明行会被自己的扫描命中，只能靠放宽判据绕过，
# 而放宽之后真实调用也一并被放过。
RETIRED_SCRIPTS = (
    "sync-" "writing-for-agents" ".py",
    "verify-" "writing-for-agents" "-install.py",
    "install-source-" "matrix-test.sh",
)
# 会真实解析脚本路径的地方：pytest 文件与 CI 工作流。注释行允许保留历史说明，
# 因为「记录曾经调用过什么」不是调用。
RETIRED_SCRIPT_CALLERS = ("tests", ".github/workflows")


def test_retired_maintenance_scripts_are_gone_and_uncalled() -> None:
    """三个维护脚本不得回到仓库，也不得再被测试或 CI 调用。

    它们校验的随包副本已退出发行集合：脚本回来意味着来源固定或安装核验被重新引入，
    而测试或 CI 仍调用它们则会让整条流水线在文件不存在时崩掉。
    """
    present = [name for name in RETIRED_SCRIPTS if (SCRIPTS / name).exists()]
    assert not present, f"已删除的维护脚本回到仓库：{present}"

    callers = [p for rel in RETIRED_SCRIPT_CALLERS
               for p in sorted((REPO / rel).rglob("*"))
               if p.is_file() and p.suffix in {".py", ".yml"}]
    offenders = []
    for path in callers:
        for line_no, line in enumerate(read(path).splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for name in RETIRED_SCRIPTS:
                if name in line:
                    offenders.append(f"{path.relative_to(REPO)}:{line_no}: {name}")
    assert not offenders, "仍在调用已删除的维护脚本：\n" + "\n".join(offenders)


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
