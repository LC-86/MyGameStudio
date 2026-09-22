"""维护脚本与文档事实的回归检查。

运行：python3.12 -m pytest tests/test_maintenance_scripts.py -q

这些断言逐条对应合并前审查发现的问题，防止同类缺陷再次进入发布内容：
不可守卫的递归删除、绑定单机缓存路径、将 CLI 的技能筛选误当作 Git 引用、
以及把宿主属性写成通用事实。
"""

from __future__ import annotations

import re
import subprocess
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
    """夹具脚本必须先校验依赖与目标安全，再创建任何东西。"""
    text = read(SCRIPTS / "behavior-fixtures.sh")
    assert "已存在且非空" in text, "缺少对非空输出目录的拒绝"
    assert "本脚本不会删除已有内容" in text, "应明确说明不会删除已有内容"
    resolve_at = text.find("resolve_skills_cli")
    mkdir_at = text.find('mkdir -p "$OUT"')
    refuse_at = text.find("已存在且非空")
    assert 0 <= resolve_at < mkdir_at, "CLI 校验必须发生在创建目录之前"
    assert 0 <= refuse_at < mkdir_at, "目标安全校验必须发生在创建目录之前"


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
