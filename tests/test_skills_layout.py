"""V3 技能源码布局与内容契约的静态检查。

运行：python3.12 -m pytest tests/test_skills_layout.py -q

这些检查覆盖发布完整性职责（原 V2 插件包测试承担的部分）：
唯一名称、标准 frontmatter、宿主调用控制契约、包内引用可达、许可通知、
旧名硬调用、客户端适配残留、游离 SKILL.md、共享资料单一所有者、Docs 消费者真实接入。
静态检查不替代真实模型行为验证，见 docs/validation-v3.md。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"

EXPECTED = frozenset({
    "ask-gamestudio", "setup-gamestudio", "grilling-gamestudio", "domain-gamestudio",
    "grill-gamestudio", "grill-gamestudio-docs", "gdd-gamestudio", "spec-gamestudio",
    "tasks-gamestudio", "implement-gamestudio", "tdd-gamestudio", "review-gamestudio",
    "debug-gamestudio", "prototype-gamestudio", "research-gamestudio",
    "wayfinder-gamestudio", "handoff-gamestudio", "codebase-gamestudio",
    "merge-gamestudio", "docs-gamestudio", "writing-for-agents",
})

USER_ENTRIES = frozenset({
    "ask-gamestudio", "setup-gamestudio", "grill-gamestudio", "grill-gamestudio-docs",
    "tasks-gamestudio", "implement-gamestudio", "wayfinder-gamestudio",
    "handoff-gamestudio",
})

# 宿主调用控制契约：8 个用户入口必须带开关，13 个按需方法两处都不得出现。
# Claude Code / Grok Build / DSH 读 frontmatter 的 disable-model-invocation；
# Codex 不读该字段，只读技能目录内 agents/openai.yaml 的 policy.allow_implicit_invocation；
# ZCode / Qoder 没有调用控制字段，由 description 措辞与正文约定兜底。
METHODS = EXPECTED - USER_ENTRIES
ENTRY_SWITCH = "disable-model-invocation"
ENTRY_SWITCH_VALUE = "true"
CODEX_POLICY_PATH = "agents/openai.yaml"
CODEX_POLICY_TEXT = "policy:\n  allow_implicit_invocation: false\n"

STANDARD_FIELDS = {"name", "description", "license", "compatibility", "metadata"}
# 宿主专属调用字段：8 个用户入口只允许 ENTRY_SWITCH 一项（下方断言先把它减掉），
# 13 个按需方法一律禁止；argument-hint / allowed-tools 在任何技能内都禁止。
FORBIDDEN_FIELDS = {
    "disable-model-invocation", "allow_implicit_invocation", "argument-hint",
    "allowed-tools", "allowed_tools",
}

# 共享资料的唯一所有者。消费者引用所有者技能的随包资料，不各存一份副本。
# 外部共同方法 `writing-for-agents` 由权威来源独立安装，GameStudio 只按技能名称取得，
# 不承诺它与 GameStudio 位于同一安装范围，因此不出现在本表。
SHARED_OWNERS = {
    "docs-gamestudio": {
        "references/document-routing.md",
        "references/delegation.md",
        "references/semantic-fidelity.md",
    },
    "tasks-gamestudio": {"references/task-responsibility.md"},
}
# 外部共同方法名：只能按技能名称取得，不能写成本仓库内的相对链接。
EXTERNAL_METHOD = "writing-for-agents"
# 按技能名称取得外部共同方法或指向游戏写作所有者的消费者。
WRITING_CONSUMERS = frozenset({
    "ask-gamestudio", "setup-gamestudio", "domain-gamestudio",
    "gdd-gamestudio", "spec-gamestudio", "tasks-gamestudio", "implement-gamestudio",
    "tdd-gamestudio", "review-gamestudio", "debug-gamestudio", "prototype-gamestudio",
    "research-gamestudio", "wayfinder-gamestudio", "handoff-gamestudio",
    "codebase-gamestudio", "merge-gamestudio", "docs-gamestudio",
})
# 通用子代理委派由 docs-gamestudio 拥有。
DELEGATION_CONSUMERS = frozenset({
    "grilling-gamestudio", "review-gamestudio", "research-gamestudio",
    "wayfinder-gamestudio", "implement-gamestudio", "tasks-gamestudio",
    "handoff-gamestudio", "ask-gamestudio", "docs-gamestudio",
})
# 按原有措辞显式点出「语义保真」的写作者，必须给出可达的保真所有者。
FIDELITY_POINTERS = frozenset({
    "domain-gamestudio", "debug-gamestudio", "prototype-gamestudio",
    "research-gamestudio", "merge-gamestudio", "codebase-gamestudio",
    "review-gamestudio", "wayfinder-gamestudio", "setup-gamestudio",
    "tdd-gamestudio", "implement-gamestudio", "handoff-gamestudio",
    "gdd-gamestudio", "spec-gamestudio",
})

# 未纳入集合的上游技能与已退役入口，不得成为消费者的硬调用目标。
NOT_SELECTED = (
    "improve-codebase-architecture", "to-questionnaire", "wait-what", "wizard",
    "teach", "triage",
)
RETIRED_ENTRIES = ("game-producer", "game-init", "game-design")
UPSTREAM_NAMES = (
    "ask-matt", "setup-matt-pocock-skills", "grill-me", "grill-with-docs",
    "grilling", "domain-modeling", "to-spec", "to-tickets", "implement", "tdd",
    "code-review", "diagnosing-bugs", "prototype", "research", "wayfinder",
    "handoff", "codebase-design", "resolving-merge-conflicts",
)

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SECRET = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16})",
)


def skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS.iterdir() if p.is_dir())


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(path: Path) -> dict[str, str]:
    text = read(path)
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, f"{path} 缺少 frontmatter"
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def md_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def test_exactly_the_twenty_one_expected_skills() -> None:
    found = {p.name for p in skill_dirs()}
    assert found == EXPECTED, f"技能集合不符：缺少 {sorted(EXPECTED - found)}，多余 {sorted(found - EXPECTED)}"
    assert len(skill_dirs()) == 21


def test_every_skill_has_exactly_one_skill_md() -> None:
    for d in skill_dirs():
        entries = sorted(p.name for p in d.rglob("SKILL.md"))
        assert entries == ["SKILL.md"], f"{d.name} 应只在目录顶层有一份 SKILL.md，实际 {entries}"


def test_directory_name_matches_frontmatter_name() -> None:
    for d in skill_dirs():
        name = frontmatter(d / "SKILL.md").get("name", "")
        assert name == d.name, f"{d.name}: frontmatter name 为 {name!r}"
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name), f"{name} 不是小写连字符名称"


def test_user_entry_frontmatter_declares_the_host_switch() -> None:
    """用户入口必须带宿主调用开关，这是 Claude Code / Grok Build / DSH 的强制点。"""
    for name in sorted(USER_ENTRIES):
        fields = frontmatter(SKILLS / name / "SKILL.md")
        assert fields.get(ENTRY_SWITCH) == ENTRY_SWITCH_VALUE, \
            f"{name}: 用户入口应声明 {ENTRY_SWITCH}: {ENTRY_SWITCH_VALUE}，" \
            f"实际 {fields.get(ENTRY_SWITCH)!r}"
        unknown = set(fields) - STANDARD_FIELDS - {ENTRY_SWITCH}
        assert not unknown, f"{name}: 非标准 frontmatter 字段 {sorted(unknown)}"
        banned = set(fields) & (FORBIDDEN_FIELDS - {ENTRY_SWITCH})
        assert not banned, f"{name}: 不得使用其他宿主专属调用字段 {sorted(banned)}"


def test_method_frontmatter_uses_standard_fields_only() -> None:
    """13 个按需方法不带宿主调用开关，只使用标准字段。"""
    for name in sorted(METHODS):
        fields = frontmatter(SKILLS / name / "SKILL.md")
        unknown = set(fields) - STANDARD_FIELDS
        assert not unknown, f"{name}: 非标准 frontmatter 字段 {sorted(unknown)}"
        banned = set(fields) & FORBIDDEN_FIELDS
        assert not banned, f"{name}: 按需方法不得带宿主专属调用开关 {sorted(banned)}"


def test_every_skill_has_description_and_license() -> None:
    for name in sorted(EXPECTED):
        fields = frontmatter(SKILLS / name / "SKILL.md")
        assert fields.get("description"), f"{name}: 缺少 description"
        assert fields.get("license") == "MIT", f"{name}: license 应为 MIT"


def test_user_entries_carry_the_codex_policy_file() -> None:
    """Codex 不读 frontmatter 开关，只读技能目录内 agents/openai.yaml。"""
    for name in sorted(USER_ENTRIES):
        agents = SKILLS / name / "agents"
        assert agents.is_dir(), f"{name}: 缺少 {CODEX_POLICY_PATH} 所在目录"
        entries = sorted(p.name for p in agents.iterdir())
        assert entries == ["openai.yaml"], f"{name}: agents/ 下只应有 openai.yaml，实际 {entries}"
        assert read(agents / "openai.yaml") == CODEX_POLICY_TEXT, \
            f"{name}: {CODEX_POLICY_PATH} 内容不符（应为 policy.allow_implicit_invocation: false）"


def test_methods_carry_no_host_specific_files() -> None:
    for name in sorted(METHODS):
        d = SKILLS / name
        assert not (d / "agents").exists(), f"{name}: 按需方法不得带 agents/ 宿主配置"
        assert not list(d.rglob("openai.yaml")), f"{name}: 按需方法不得带 Codex 策略文件"


def test_descriptions_state_the_invocation_boundary() -> None:
    """8 个用户入口的描述必须说明它由用户请求触发；其余说明按需适用情境。"""
    for d in skill_dirs():
        desc = frontmatter(d / "SKILL.md")["description"]
        if d.name in USER_ENTRIES:
            assert re.search(r"用户(请求|使用|询问|要求)", desc), \
                f"{d.name} 是用户入口，description 应说明由用户请求触发"
        assert len(desc) <= 1024, f"{d.name}: description 过长（{len(desc)}）"


def test_every_skill_carries_its_own_license_notice() -> None:
    for d in skill_dirs():
        lic = d / "LICENSE"
        assert lic.is_file(), f"{d.name}: 缺少随技能分发的 LICENSE 通知"
        text = read(lic)
        assert "MIT License" in text, f"{d.name}: LICENSE 缺少 MIT 许可全文"
        assert "LC-86 / MyGameStudio" in text, f"{d.name}: LICENSE 缺少本项目版权"
        assert d.name in text, f"{d.name}: LICENSE 未标明所属技能"
        if d.name != "gdd-gamestudio":
            assert "Matt Pocock" in text, f"{d.name}: 改编技能应保留上游署名"


def test_all_relative_references_resolve() -> None:
    broken = []
    for path in md_files(SKILLS):
        for raw in LINK.findall(read(path)):
            if raw.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = (path.parent / raw.split("#", 1)[0]).resolve()
            if not target.exists():
                broken.append(f"{path.relative_to(REPO)} -> {raw}")
    assert not broken, "包内引用不可达：\n" + "\n".join(broken)


def test_no_client_adapter_residue() -> None:
    """除用户入口的 Codex 策略文件外，技能目录不得有其他客户端适配残留。"""
    allowed = {(name, "openai.yaml") for name in USER_ENTRIES}
    residue = []
    for path in sorted(SKILLS.rglob("*")):
        rel = path.relative_to(REPO).as_posix()
        if path.name.startswith((".claude-plugin", ".codex-plugin", ".zcode-plugin")):
            residue.append(rel)
        elif path.name == "openai.yaml":
            owner = path.parent.parent.name if path.parent.name == "agents" else None
            if (owner, path.name) not in allowed:
                residue.append(rel)
        elif path.is_dir() and path.name == "agents" and path.parent.name not in USER_ENTRIES:
            residue.append(rel)
    assert not residue, f"技能目录内残留客户端适配：{residue}"


def test_shared_references_have_a_single_owner() -> None:
    """共享方法只有一份权威正文，消费者引用所有者技能的随包资料。"""
    for owner, rels in SHARED_OWNERS.items():
        for rel in rels:
            assert (SKILLS / owner / rel).is_file(), f"缺少共享资料 {owner}/{rel}"
    duplicates = []
    for rel in ("document-routing.md", "subagent-delegation.md", "SKILL-MECHANICS.md",
                "semantic-fidelity.md", "delegation.md", "task-responsibility.md"):
        hits = sorted(p.relative_to(SKILLS).as_posix() for p in SKILLS.rglob(rel))
        assert len(hits) == 1, f"{rel} 应只有一份权威正文，实际 {hits}"
    for d in skill_dirs():
        for path in md_files(d):
            for raw in LINK.findall(read(path)):
                if raw.startswith(("http://", "https://", "#")):
                    continue
                target = (path.parent / raw.split("#", 1)[0]).resolve()
                try:
                    rel_to_skills = target.relative_to(SKILLS)
                except ValueError:
                    duplicates.append(f"{path.relative_to(REPO)} -> {raw} 逃出 skills/")
                    continue
                owner = rel_to_skills.parts[0]
                if owner == d.name:
                    continue
                # 指向另一项技能正文是中性调用表达；指向其随包资料只允许共享所有者
                if rel_to_skills.name == "SKILL.md":
                    continue
                if rel_to_skills.as_posix() in {f"{owner}/{r}"
                                                for r in SHARED_OWNERS.get(owner, ())}:
                    continue
                duplicates.append(
                    f"{path.relative_to(REPO)} -> {raw}：跨技能引用了 {owner} 的私有资料")
    assert not duplicates, "共享资料归属被破坏：\n" + "\n".join(duplicates)


def test_external_method_gap_has_a_declared_handling() -> None:
    """缺外部共同方法时的处理写进所有者正文，而不是留给读者猜。

    静态检查只能证明契约文本存在；真实缺口场景的宿主行为见验证记录，
    未运行时标为 not-run，不用本测试代替。
    """
    body = read(SKILLS / "docs-gamestudio" / "SKILL.md")
    assert "按宿主支持的技能名称取得它" in body, \
        "docs-gamestudio 应按宿主支持的技能名称取得外部方法"
    assert "说明具体缺口和受影响的工作" in body, \
        "docs-gamestudio 应说明缺外部方法时指出缺口与受影响工作"
    assert "只继续不依赖它的部分" in body, \
        "docs-gamestudio 应说明只继续不依赖该方法的部分"
    assert "不凭名称模仿缺失的方法" in body, \
        "docs-gamestudio 应禁止模仿缺失方法后宣称已取得"


def test_no_cross_scope_relative_paths_to_the_external_method() -> None:
    """外部共同方法只能按技能名称取得，不得写成跨安装范围的相对链接。

    随包副本可能在后续收缩中退出发行集合；指向它的相对路径会把安装布局
    当成依赖契约，因此这里的检查与随包副本是否存在无关。
    """
    offenders = []
    for d in skill_dirs():
        if d.name == EXTERNAL_METHOD:
            continue
        for path in md_files(d):
            rel = path.relative_to(REPO).as_posix()
            for raw in LINK.findall(read(path)):
                if raw.startswith(("http://", "https://", "#")):
                    continue
                if f"{EXTERNAL_METHOD}/" in raw:
                    offenders.append(f"{rel} -> {raw}：把外部共同方法写成了包内相对链接")
    assert not offenders, "外部方法被写成本范围相对路径：\n" + "\n".join(offenders)


def test_no_hard_calls_to_retired_or_unselected_skills() -> None:
    offenders = []
    attribution = ("适配自", "上游", "原版", "Matt")
    delimited = lambda name: rf"[`(\[]\s*{re.escape(name)}\s*[`)\]]"
    for path in md_files(SKILLS):
        text = read(path)
        rel = path.relative_to(REPO).as_posix()
        for name in NOT_SELECTED + UPSTREAM_NAMES:
            kind = "未纳入技能" if name in NOT_SELECTED else "上游原名"
            for line in text.splitlines():
                # 来源署名允许保留原名；作为调用目标不允许
                if re.search(delimited(name), line) and not any(a in line for a in attribution):
                    offenders.append(f"{rel}: 以{kind} {name} 作为调用目标")
    # 退役入口只允许出现在 setup 的失效引用处理段落与许可/来源说明中
    for path in md_files(SKILLS):
        rel = path.relative_to(REPO).as_posix()
        if rel == "skills/setup-gamestudio/SKILL.md":
            continue
        for name in RETIRED_ENTRIES:
            if name in read(path):
                offenders.append(f"{rel}: 提及已退役入口 {name}")
    assert not offenders, "旧名硬调用：\n" + "\n".join(sorted(set(offenders)))


# Issue #92：游戏设计与文档工作流组。这些流程在正式资料分支按技能名称取得外部
# 共同方法，同时继续用 GameStudio 的分流、保真与委派参考，并各自保留启动、
# 返回和停止条件（不因外部依赖串成新的自动工作流）。
GAME_DOC_FLOWS = {
    # 名称: (启动/适用条件（取自 description，宿主发现时读到的就是它）, 返回或停止边界)
    "docs-gamestudio": ("需要组织子代理派发与结果核对时使用",
                        "有用的参考读完后返回原任务"),
    "domain-gamestudio": ("只读取既有术语时无需启动",
                          "完成当前部分后回到原讨论"),
    "gdd-gamestudio": ("在已授权的讨论文档协作中",
                       "完成这一轮更新便回到原问题集"),
    "spec-gamestudio": ("将当前已确认的功能、系统、资源或变更要求整理为具体工作规格",
                        "完成当前更新即返回原问答"),
    "grilling-gamestudio": ("用户希望梳理想法、比较取舍",
                            "在当前目标清楚时收束"),
    "prototype-gamestudio": ("用于用户明确要求原型或当前任务已包含实验制作",
                             "到本次原型交付或验证结论为止"),
    "wayfinder-gamestudio": ("用户请求为一个需要跨会话澄清的大型游戏目标梳理路线时使用",
                             "在目的达到时交接"),
}
# 正式写作分支必须自带缺外部方法的处理：单独调用本流程时只读得到它自己，
# 不能指望每一个调用都先去读所有者正文。
GAP_CLAUSE = "无法取得时说明具体缺口和受影响的工作，只继续不依赖它的部分，不模仿缺失的方法"
GAME_DOC_WRITERS = ("docs-gamestudio", "domain-gamestudio", "gdd-gamestudio",
                    "spec-gamestudio", "prototype-gamestudio", "wayfinder-gamestudio")


def test_game_document_flows_keep_their_own_boundaries() -> None:
    """本组各流程保留自己的启动条件与返回/停止边界，外部方法来源变化不改变它们。

    启动条件取自 description（宿主发现技能时读到的就是它），返回/停止边界在正文里。
    """
    missing = []
    for name, (start_marker, stop_marker) in sorted(GAME_DOC_FLOWS.items()):
        description = frontmatter(SKILLS / name / "SKILL.md")["description"]
        if start_marker not in description:
            missing.append(f"{name}: description 缺少启动/适用条件 {start_marker!r}")
        if stop_marker not in read(SKILLS / name / "SKILL.md"):
            missing.append(f"{name}: 缺少返回/停止边界 {stop_marker!r}")
    assert not missing, "游戏设计与文档流程丢失自身边界：\n" + "\n".join(missing)


def test_game_document_writers_declare_the_missing_method_handling() -> None:
    """本组写作者各自说明缺外部共同方法时的处理，不只依赖所有者正文。"""
    missing = []
    for name in GAME_DOC_WRITERS:
        body = read(SKILLS / name / "SKILL.md")
        if f"`{EXTERNAL_METHOD}`" not in body:
            missing.append(f"{name}: 没有按技能名称说明外部共同方法")
        if name == "docs-gamestudio":
            continue  # 所有者正文用完整措辞，由 test_external_method_gap_has_a_declared_handling 断言
        if GAP_CLAUSE not in body:
            missing.append(f"{name}: 缺少缺外部方法时的处理说明")
    assert not missing, "游戏文档写作者的缺方法处理缺失：\n" + "\n".join(missing)


def test_writing_consumers_resolve_the_method_by_skill_name() -> None:
    """写作者按技能名称取得外部共同方法，并指向真正拥有该内容的资料。"""
    routing_consumers = {
        "grilling-gamestudio", "domain-gamestudio", "gdd-gamestudio", "spec-gamestudio",
        "implement-gamestudio", "prototype-gamestudio", "wayfinder-gamestudio",
    }
    missing = []
    for name in sorted(WRITING_CONSUMERS):
        body = read(SKILLS / name / "SKILL.md")
        if re.search(rf"\[[^\]]*\]\([^)]*{EXTERNAL_METHOD}", body):
            missing.append(f"{name}: 用相对链接而不是技能名称取得外部共同方法")
        if not re.search(rf"`?{EXTERNAL_METHOD}`?", body):
            missing.append(f"{name}: 没有说明外部共同方法 writing-for-agents")
        if "../docs-gamestudio/SKILL.md" in body:
            missing.append(f"{name}: 仍把 docs-gamestudio 当成共同写作方法正文")
    for name in sorted(FIDELITY_POINTERS):
        body = read(SKILLS / name / "SKILL.md")
        if "../docs-gamestudio/references/semantic-fidelity.md" not in body:
            missing.append(f"{name}: 保真要求没有指向语义保真所有者")
    for name in sorted(DELEGATION_CONSUMERS):
        body = read(SKILLS / name / "SKILL.md")
        # 所有者自身用包内相对路径；消费者用技能相对路径
        if ("../docs-gamestudio/references/delegation.md" not in body
                and not (name == "docs-gamestudio" and "references/delegation.md" in body)):
            missing.append(f"{name}: 委派点没有链接 docs-gamestudio 的委派参考")
    for name in sorted(routing_consumers):
        body = read(SKILLS / name / "SKILL.md")
        if "../docs-gamestudio/references/document-routing.md" not in body:
            missing.append(f"{name}: 文档分流点没有链接 document-routing.md")
    assert not missing, "写作与委派消费者接入缺失：\n" + "\n".join(missing)


def test_docs_owns_fidelity_delegation_and_game_routing() -> None:
    """docs-gamestudio 重新拥有语义保真与通用委派，且保留游戏文档分流入口。"""
    body = read(SKILLS / "docs-gamestudio" / "SKILL.md")
    assert EXTERNAL_METHOD in body, "docs-gamestudio 应说明外部共同方法的取得方式"
    for rel in ("references/semantic-fidelity.md", "references/delegation.md",
                "references/document-routing.md"):
        assert rel.split("/")[-1] in body, f"docs-gamestudio 应保留 {rel} 入口"
    assert "递归调用链" in body and "审批" in body, "docs-gamestudio 应说明其非递归、非审批边界"
    assert "不写跨安装范围的相对路径" in body, "docs-gamestudio 应说明不写跨范围相对路径"
    assert not (SKILLS / "docs-gamestudio" / "references/skill-authoring.md").exists(), \
        "技能机制仍由共同方法承担，本票不收回 skill-authoring"


def test_semantic_fidelity_contract_is_complete() -> None:
    """保真契约显式覆盖工单列出的各项，身份不升级也不合并。"""
    text = read(SKILLS / "docs-gamestudio" / "references" / "semantic-fidelity.md")
    for marker in ("数字", "单位", "顺序", "条件", "例外", "排除项", "责任",
                   "确认状态", "原始证据"):
        assert marker in text, f"semantic-fidelity.md 缺少 {marker}"
    for marker in ("建议", "试验值", "已采纳设计", "已实现", "已验证"):
        assert marker in text, f"semantic-fidelity.md 缺少身份标记 {marker}"
    assert "不因整理而升级或合并" in text, "保真契约应说明身份不升级、不合并"
    assert "指出这里需要一个决定" in text, "原文含糊时保真契约应要求指出缺口而不是补写答案"


def test_delegation_contract_covers_brief_and_return_check() -> None:
    """通用委派参考覆盖派发说明各项、上下文继承边界与结果回收核对。"""
    text = read(SKILLS / "docs-gamestudio" / "references" / "delegation.md")
    for marker in ("目标", "来源版本", "可访问输入", "授权", "自主空间",
                   "上下文继承", "完成证据", "受阻处理", "结果回收核对"):
        assert marker in text, f"delegation.md 缺少 {marker}"
    assert "父代理取得过一份方法不等于子代理拥有它" in text, \
        "委派参考应说明父代理的方法不自动进入接收方"
    assert "不递归派发" in text and "收回结果后核对" in text, \
        "委派参考应说明不递归派发与回收核对"


def test_writing_for_agents_pin_and_package_digests() -> None:
    """随包内容固定到 #86 的源提交，manifest 能校验发行副本。"""
    skill = SKILLS / "writing-for-agents"
    source = read(skill / "SOURCE.md")
    commit = "f3c726f275fa1ac59fef33732e527dded6d62479"
    assert "LC-86/mattpocockskills" in source
    assert commit in source
    assert "agents/openai.yaml" in source and "not included" in source
    mechanics = read(skill / "SKILL-MECHANICS.md")
    assert "## Codex invocation policy" in mechanics
    assert "Codex uses the skill-local `agents/openai.yaml` policy instead" in mechanics
    assert "allow_implicit_invocation: false" in mechanics
    assert "frontmatter field alone prevents Codex" in mechanics
    assert "fixed Codex invocation-policy note" in source

    sums = {}
    for line in read(skill / "SHA256SUMS").splitlines():
        digest, _, rel = line.partition("  ")
        assert re.fullmatch(r"[0-9a-f]{64}", digest), f"摘要格式错误：{line}"
        sums[rel] = digest
    expected = {p.relative_to(skill).as_posix() for p in skill.rglob("*")
                if p.is_file() and p.name != "SHA256SUMS"}
    assert set(sums) == expected, "SHA256SUMS 必须覆盖全部随包文件（不含自身）"
    import hashlib
    for rel, digest in sums.items():
        actual = hashlib.sha256((skill / rel).read_bytes()).hexdigest()
        assert actual == digest, f"随包文件摘要不符：{rel}"


def test_responsibility_semantics_are_present() -> None:
    """ready-for-agent / ready-for-human 的含义与人工验收边界只在所有者处维护。"""
    text = read(SKILLS / "tasks-gamestudio" / "references" / "task-responsibility.md")
    for marker in ("ready-for-agent", "ready-for-human", "下一执行段",
                   "人工项保持未完成", "不是权限凭证"):
        assert marker in text, f"task-responsibility.md 缺少 {marker}"
    impl = read(SKILLS / "implement-gamestudio" / "SKILL.md")
    assert "人工确认未完成时" in impl, "implement 应保留人工验收未完成不关单的边界"


def test_gdd_spec_cross_call_has_stop_conditions() -> None:
    gdd = read(SKILLS / "gdd-gamestudio" / "SKILL.md")
    spec = read(SKILLS / "spec-gamestudio" / "SKILL.md")
    routing = read(SKILLS / "docs-gamestudio" / "references" / "document-routing.md")
    assert "只完成该差异并返回" in gdd, "GDD 被 spec 请求时应只处理差异并返回"
    assert "不将相同内容立即反向交回" in spec, "spec 被 GDD 请求时不得立即反调"
    assert "不是原子事务" in routing or "不宣称两者已一致" in routing, \
        "分流约定应说明多文档写入不是原子事务"
    assert "停止调用" in routing, "分流约定应给出停止条件"


def test_prototype_requires_a_playable_browser_game() -> None:
    body = read(SKILLS / "prototype-gamestudio" / "SKILL.md")
    for marker in ("可玩的浏览器小游戏", "SVG", "实际输入", "状态面板", "重置"):
        assert marker in body, f"prototype 缺少 {marker} 相关约束"


def test_no_dev_machine_paths_or_secrets_in_shipped_content() -> None:
    offenders = []
    for path in sorted(SKILLS.rglob("*")):
        if not path.is_file() or path.suffix in {".pyc", ".pyo"}:
            continue
        text = path.read_text(errors="replace")
        if "/Users/" in text or "/home/" in text:
            offenders.append(f"{path.relative_to(REPO)}: 含开发机绝对路径")
        if SECRET.search(text):
            offenders.append(f"{path.relative_to(REPO)}: 疑似凭据")
    assert not offenders, "\n".join(offenders)


def publishable_files() -> list[str]:
    """会被发布的文件集合：存在于工作树，且已跟踪或未跟踪但未被忽略。

    被 .gitignore 排除的本地残留不进入发布内容，因此不算有效技能发现风险；
    已删除但仍在索引中的退役文件也不算，它们不存在于源码树。
    """
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    return [line for line in out if line.strip() and (REPO / line).is_file()]


def test_no_stray_skill_md_outside_skills_dir() -> None:
    """历史材料、夹具与旧安装产物不得被官方 CLI 发现为有效技能。"""
    stray = []
    for rel in publishable_files():
        if not rel.endswith("SKILL.md"):
            continue
        parts = rel.split("/")
        if len(parts) == 3 and parts[0] == "skills":
            continue
        stray.append(rel)
    assert not stray, f"发布内容中发现游离 SKILL.md：{stray}"


def test_no_retired_trees_in_publishable_content() -> None:
    """已退役的插件适配、运行层与旧交付物不得留在源码树或发布内容里。"""
    retired_dirs = ("plugin", "legacy", "dist", "acceptance", "samples", "examples",
                    "docs/installation", "docs/skills")
    present = [d for d in retired_dirs if (REPO / d).exists()]
    assert not present, f"源码树仍含已退役目录：{present}"
    banned = (".claude-plugin", ".codex-plugin", ".zcode-plugin")
    hits = [rel for rel in publishable_files() if any(b in rel for b in banned)]
    assert not hits, f"发布内容仍含客户端适配：{hits[:20]}"
    allowed_policy = {f"skills/{name}/{CODEX_POLICY_PATH}" for name in USER_ENTRIES}
    stray_policy = [rel for rel in publishable_files()
                    if "openai.yaml" in rel and rel not in allowed_policy]
    assert not stray_policy, f"发布内容含未授权的 Codex 策略文件：{stray_policy[:20]}"


def test_no_root_level_aggregate_skill_md() -> None:
    assert not (REPO / "SKILL.md").exists(), "根目录不得有聚合 SKILL.md"
    assert not (SKILLS / "SKILL.md").exists(), "skills/ 下不得有聚合 SKILL.md"


@pytest.mark.parametrize("entry", sorted(USER_ENTRIES))
def test_user_entries_do_not_auto_chain(entry: str) -> None:
    """用户入口不自行开启其他用户入口的工作流程。"""
    body = read(SKILLS / entry / "SKILL.md")
    others = USER_ENTRIES - {entry, "grill-gamestudio", "grill-gamestudio-docs"}
    for other in others:
        assert not re.search(rf"\[[^\]]*\]\(\.\./{other}/SKILL\.md\)", body), \
            f"{entry} 链接了另一个用户入口 {other}，用户入口之间不得自动串调"
