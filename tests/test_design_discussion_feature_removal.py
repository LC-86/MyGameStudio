#!/usr/bin/env python3
"""统一设计问答框架票 07:完整处理功能删减。

接缝:``plugin/skills/game-design/removal.py`` 的 ``plan_removal`` /
``apply_removal`` / ``verify_removal``(原作用盘点在 ``removal_impact.py``)。
固定小型游戏(齿轮谜城)删除同时承担奖励与引导作用的「每日挑战」:盘点原作用
与关联、追踪残留依赖与间接引用、区分三类作用处理与取消范围,只对尚未明确
且影响体验的处理方式提问;获准同步后失效规则、旧入口与旧验收退出而历史保留,
产品代码、资源与用户数据不动。期望值来自工单与规格字面量及固定场景语义,
只经公共接口观察行为,不测内部函数。

    python3 -B tests/test_design_discussion_feature_removal.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from plugin_package_support import PLUGIN_ROOT, REPO_ROOT, make_checker, run_theme
from runtime_gate_support import GateService

FAILURES, check = make_checker()

SKILL_DIR = PLUGIN_ROOT / "skills" / "game-design"
LEGACY_DESIGN_ENTRY = REPO_ROOT / "legacy" / "game-design-discussion-entry.md"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from change_flow import answer_turn  # noqa: E402
from decisions import plan_save  # noqa: E402
from removal import apply_removal, plan_removal, verify_removal  # noqa: E402
from rounds import run_round  # noqa: E402

RECORDS = "docs/mygamestudio/records"
SPEC_DAILY_REL = f"{RECORDS}/spec-每日挑战.md"
SPEC_GROWTH_REL = f"{RECORDS}/spec-成长资源.md"
SPEC_GUIDE_REL = f"{RECORDS}/spec-界面引导.md"
SPEC_CHAPTER_REL = f"{RECORDS}/spec-章节.md"
CHANGE_REL = f"{RECORDS}/change-删除每日挑战.md"
DECISION_REL = f"{RECORDS}/decisions-每日挑战.md"
DESIGN_REL = "docs/mygamestudio/GAME_DESIGN.md"
PROJECT_REL = "docs/mygamestudio/PROJECT.md"
TECH_REL = "docs/mygamestudio/TECH_DESIGN.md"
CODE_REL = "src/daily.js"
SAVE_REL = "data/player-save.json"
DATE = "2026-09-14"

DAILY_SPEC = """# 每日挑战：模块规格

## 正常规则
- 每日挑战:每天一关,当日仅一次结算。
- 主菜单显示「每日挑战」入口。
- 内容：每日关从现有 20 关按日期轮换。

## 数据与持续性
- 存档保存当日最佳步数（键 dayBest）。

## 验收方式
- 验收：当日重复进行时只保留更优成绩。
"""

GROWTH_SPEC = """# 成长资源：模块规格

## 正常规则
- 每日结算齿轮币 3 枚,日上限 3 枚。
- 章节解锁需齿轮币 30 枚。
"""

GUIDE_SPEC = """# 界面引导与教程：模块规格

## 正常规则
- 新手教程第 3 步引导玩家进入每日挑战。
"""

CHAPTER_SPEC = """# 章节：模块规格

## 正常规则
- 章节按关卡顺序解锁,与每日挑战无关。
"""

SAVE_TEXT = '{"dayBest": 42, "chapter": 2}\n'


def _service(root: Path, *, product_write=False):
    project = root / "project"
    (project / "docs/mygamestudio/records").mkdir(parents=True)
    (project / "src").mkdir(parents=True)
    (project / "data").mkdir(parents=True)
    (project / SPEC_DAILY_REL).write_text(DAILY_SPEC, encoding="utf-8")
    (project / SPEC_GROWTH_REL).write_text(GROWTH_SPEC, encoding="utf-8")
    (project / SPEC_GUIDE_REL).write_text(GUIDE_SPEC, encoding="utf-8")
    (project / SPEC_CHAPTER_REL).write_text(CHAPTER_SPEC, encoding="utf-8")
    (project / DESIGN_REL).write_text(
        "# 齿轮谜城:当前游戏需求与设计\n\n基线版本:v2。\n\n"
        "## 本轮可执行规格（2026-09-01，v1 → v2）\n\n"
        f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_DAILY_REL}。\n\n"
        "内容指纹：sha256:" + "0" * 64 + "\n"
        "归一指纹：sha256:" + "0" * 64 + "\n", encoding="utf-8")
    (project / PROJECT_REL).write_text(
        "# 项目目标\n\n当前版本只做主线 20 关。\n", encoding="utf-8")
    (project / TECH_REL).write_text(
        "# 技术设计\n\n存档为本地 JSON。\n", encoding="utf-8")
    (project / CODE_REL).write_text(
        "// 每日挑战实现:dayBest 每日最佳\n", encoding="utf-8")
    (project / SAVE_REL).write_text(SAVE_TEXT, encoding="utf-8")
    (project / DECISION_REL).write_text(
        "# 每日挑战：决定记录\n\n## 第 1 轮 2026-09-01\n"
        "- 决定者：开发者。日期：2026-09-01。\n- 用户回复：「Q1 选 A」\n"
        "- D 每日挑战·Q1 关卡来源：采纳 A\n"
        "  - 来源：开发者第 1 轮作答\n  - 建议出处：Q1 推荐 A\n"
        "  - 影响：决定每日关的复用方式。\n  - 同步状态：已同步\n",
        encoding="utf-8")
    roles = {"design": ["docs/mygamestudio/records/**", DESIGN_REL]}
    purposes = {"design_discussion": ["docs/mygamestudio/records/**"],
                "change_sync": ["docs/mygamestudio/records/**", DESIGN_REL]}
    if product_write:
        roles["design"].extend([CODE_REL, "data/**"])
        purposes["change_sync"].extend([CODE_REL, "data/**"])
    svc = GateService(root / "runtime")
    svc.init_policy(project_root=project, roles=roles, purposes=purposes)
    return svc, project


def _instance(svc, purpose="change_sync", resources=None):
    return svc.create_instance(
        role="design", task="G02", purpose=purpose,
        resources=list(resources or ["docs/mygamestudio/records/**",
                                     DESIGN_REL]),
        ttl_seconds=1800)


class _Channel:
    """测试用通道适配:与 mgs-gate 提交同一条 GateService 受控写入路径。"""

    def __init__(self, svc, token):
        self.svc = svc
        self.token = token
        self.writes = []

    def scope(self):
        return self.svc.scope(self.token)

    def write(self, path, content, expected_sha256=None, note=None):
        self.writes.append({"path": path, "expected_sha256": expected_sha256})
        return self.svc.write(self.token, path, content,
                              expected_sha256=expected_sha256, note=note)


def _reader(project: Path):
    def read(path: str):
        target = project / path
        return target.read_text(encoding="utf-8") if target.is_file() else None
    return read


def _items():
    """现行设计元素:每日挑战是被删对象,其余按实际依赖与它关联。"""

    return [
        {"id": "daily_cadence", "module": "每日挑战", "lane": "rules",
         "title": "每日挑战节奏", "location": SPEC_DAILY_REL,
         "old_text": "- 每日挑战:每天一关,当日仅一次结算。",
         "new_text": "- 已取消每日挑战模块,不再提供每日关卡与每日结算。",
         "removal_action": "cancel",
         "resolution": "每日挑战随删减取消。"},
        {"id": "daily_reward", "module": "成长资源", "lane": "growth",
         "title": "周期奖励结算", "location": SPEC_GROWTH_REL,
         "old_text": "- 每日结算齿轮币 3 枚,日上限 3 枚。",
         "new_text": "- 章节完成结算齿轮币 21 枚（原每日结算已随每日挑战"
                     "取消转移至此）。",
         "depends_on": ["daily_cadence"], "removal_action": "reconfigure",
         "resolution": "奖励来源转移给章节结算。"},
        {"id": "unlock_cost", "module": "成长资源", "lane": "growth",
         "title": "章节解锁条件", "location": SPEC_GROWTH_REL,
         "old_text": "- 章节解锁需齿轮币 30 枚。",
         "depends_on": ["daily_reward"], "removal_action": "reconfigure"},
        {"id": "menu_entry", "module": "每日挑战", "lane": "ui",
         "title": "主菜单每日入口", "location": SPEC_DAILY_REL,
         "old_text": "- 主菜单显示「每日挑战」入口。",
         "new_text": "- 主菜单移除「每日挑战」入口,不设同类替代入口。",
         "depends_on": ["daily_cadence"], "removal_action": "cancel",
         "resolution": "入口随功能一起取消。"},
        {"id": "tutorial_step", "module": "界面引导与教程", "lane": "ui",
         "title": "新手教程引导步骤", "location": SPEC_GUIDE_REL,
         "old_text": "- 新手教程第 3 步引导玩家进入每日挑战。",
         "new_text": "- 新手教程移除每日挑战步骤,本版不含该步引导。",
         "depends_on": ["daily_cadence"], "removal_action": "cancel",
         "resolution": "教程步骤随功能一起取消。"},
        {"id": "pool", "module": "每日挑战", "lane": "content",
         "title": "每日关轮换内容", "location": SPEC_DAILY_REL,
         "old_text": "- 内容：每日关从现有 20 关按日期轮换。",
         "new_text": "- 内容：20 关全部并入章节关卡池,不再按日期轮换。",
         "depends_on": ["daily_cadence"], "removal_action": "reconfigure",
         "resolution": "关卡内容保留,轮换机制重新配置。"},
        {"id": "save", "module": "每日挑战", "lane": "data",
         "title": "当日最佳存档", "location": SPEC_DAILY_REL,
         "old_text": "- 存档保存当日最佳步数（键 dayBest）。",
         "new_text": "- 不再写入 dayBest;旧档 dayBest 只读保留。",
         "depends_on": ["daily_cadence"], "removal_action": "cancel",
         "resolution": "写入随功能一起取消,旧档只读保留。"},
        {"id": "acceptance_daily", "module": "每日挑战", "lane": "acceptance",
         "title": "每日验收用例", "location": SPEC_DAILY_REL,
         "old_text": "- 验收：当日重复进行时只保留更优成绩。",
         "new_text": "- 每日验收用例随功能取消,退出当前有效版本。",
         "depends_on": ["daily_cadence"], "removal_action": "cancel",
         "resolution": "旧验收要求退出现行版本。"},
        {"id": "chapter_order", "module": "章节", "lane": "rules",
         "title": "章节进度", "location": SPEC_CHAPTER_REL,
         "old_text": "- 章节按关卡顺序解锁,与每日挑战无关。",
         "unaffected_reason": "章节解锁按关卡顺序,不依赖每日挑战或其产出"},
    ]


def _roles():
    """原作用盘点:八个方面逐项给出作用、关联与处理方式。"""

    return [
        {"id": "reward_source", "lane": "reward", "title": "齿轮币奖励来源",
         "detail": "每日结算 3 枚齿轮币是主要成长来源",
         "items": ["daily_reward"],
         "disposition": "transfer", "successor": "章节结算",
         "successor_detail": "每章完成结算 21 枚齿轮币"},
        {"id": "guidance", "lane": "guidance", "title": "每日行动引导",
         "detail": "每日节奏形成每天上线的引导",
         "items": ["daily_cadence"],
         "disposition": "simplify", "successor": "章节进度提示",
         "successor_detail": "主菜单显示章节进度,不再设置每日入口"},
        {"id": "unlock", "lane": "unlock", "title": "章节解锁节奏",
         "detail": "齿轮币 30 枚解锁章节,构成成长节奏",
         "items": ["unlock_cost"],
         "options": {"A": "简化保留:章节解锁改为按关卡数,不再用齿轮币",
                     "B": "转移给已有系统:解锁门槛移交章节结算的累计奖励"},
         "option_effects": {
             "A": {"disposition": "simplify", "successor": "按关卡数解锁"},
             "B": {"disposition": "transfer", "successor": "章节结算"}},
         "recommendation": "A",
         "reason": "保留成长节奏且不恢复每日压力",
         "impact": "影响成长节奏与解锁体验"},
        {"id": "entry", "lane": "entry", "title": "主菜单每日入口",
         "detail": "「每日挑战」入口承担每日行动引导",
         "items": ["menu_entry"],
         "disposition": "cancel",
         "disposition_detail": "入口随功能移除,不设同类新入口"},
        {"id": "tutorial", "lane": "tutorial", "title": "新手教程引导步骤",
         "detail": "教程第 3 步依赖每日挑战",
         "items": ["tutorial_step"],
         "disposition": "cancel", "disposition_detail": "旧步骤本版移除",
         "scope": "promised",
         "promise": "下一版本提供一个不依赖每日挑战的新手引导步骤",
         "scope_basis": "本轮讨论中开发者已明确承诺"},
        {"id": "content", "lane": "content", "title": "每日关轮换内容",
         "detail": "每日关从现有 20 关按日期轮换",
         "items": ["pool"],
         "disposition": "cancel",
         "disposition_detail": "不再需要每日轮换,20 关并入章节关卡池"},
        {"id": "save_data", "lane": "data", "title": "当日最佳存档",
         "detail": "存档 dayBest 记录当日最佳步数,已发布玩家持有记录",
         "items": ["save"],
         "options": {
             "A": "停写 dayBest,旧档只读保留;清理旧档本版不做",
             "B": "转移给章节最佳成绩键,旧档迁移"},
         "option_effects": {
             "A": {"disposition": "cancel", "scope": "not_now",
                   "scope_basis": "清理涉及玩家数据,本版不做,"
                                  "未承诺后续版本"},
             "B": {"disposition": "transfer", "successor": "章节最佳成绩"}},
         "recommendation": "A",
         "reason": "不丢玩家记录,清理动作需另行授权",
         "impact": "影响已有存档与玩家进度"},
        {"id": "acceptance_daily", "lane": "acceptance", "title": "每日验收用例",
         "detail": "验收要求当日重复进行时只保留更优成绩",
         "items": ["acceptance_daily"],
         "disposition": "cancel",
         "disposition_detail": "旧验收退出当前有效版本"},
    ]


def _data_handling():
    return {
        "existing_data": {
            "plan": "旧档 dayBest 只读保留,不再写入",
            "actions": ["在实现中停止写入 dayBest", "清理旧档 dayBest 键"]},
        "player_progress": {"plan": "已有当日最佳成绩保留展示,不回收"},
        "pending_resources": {"exists": False},
        "entitlements": {"exists": False},
    }


def _objects(stage):
    base = {
        "rules": {"exists": True, "evidence": "模块规格已有独立规则"},
        "flow": {"exists": True, "evidence": "首次进入到再次进入已推演"},
        "numbers": {"exists": True, "evidence": "规格数值表已给单位与范围"},
        "content_list": {"exists": True, "evidence": "内容清单列出现有 20 关"},
        "acceptance": {"exists": True, "evidence": "规格含验收方式"},
    }
    if stage == "design_only":
        return base
    base.update({
        "implementation": {"exists": True, "evidence": "src/daily.js 已实现"},
        "ui": {"exists": True, "evidence": "主菜单入口已上线"},
        "resources": {"exists": False, "evidence": "无外部美术资源改动"},
        "tests": {"exists": True, "evidence": "tests/daily.test.js 三条用例"},
        "existing_data": {"exists": True, "evidence": "本机存档含 dayBest"},
        "save_compat": {"exists": True, "evidence": "旧档需要兼容读取"},
    })
    if stage == "released":
        base.update({
            "player_progress": {"exists": True,
                                "evidence": "已有玩家持有当日最佳记录"},
            "pending_resources": {"exists": False, "evidence": "无待领资源"},
            "entitlements": {"exists": False, "evidence": "免费游戏无付费权益"},
            "migration": {"exists": True, "evidence": "需要旧档迁移说明"},
            "release_plan": {"exists": True, "evidence": "需要商店更新公告"},
        })
    return base


def _removal(**over):
    block = {
        "targets": ["daily_cadence"],
        "target_labels": ["每日挑战"],
        "reason": "每日负担重,与轻量方向冲突",
        "improvement": "去掉被迫每日上线的负担",
        "keep": ["现有 20 关关卡内容", "章节进度与解锁", "本机离线可玩"],
        "roles": _roles(),
        "data_handling": _data_handling(),
    }
    block.update(over)
    return block


def _material(**over):
    """固定删减场景:删除同时承担奖励与引导作用的「每日挑战」。"""

    material = {
        "game": "齿轮谜城",
        "request": {"text": "每日挑战太肝,删掉",
                    "state": "decided",
                    "decided_direction": "删除每日挑战"},
        "removal": _removal(),
        "stage": "released",
        "stage_basis": "已发布,有实际玩家与存档",
        "depth": "module",
        "objects": _objects("released"),
        "design_items": _items(),
        "scenarios": {
            "new_player": {"applies": True, "findings": [
                {"text": "新玩家首章即可看到进度提示,不再被每日入口要求",
                 "kind": "consistency", "status": "ok"}]},
            "existing_progress": {"applies": True, "findings": [
                {"text": "旧档 dayBest 只读保留,既有记录不丢失",
                 "kind": "consistency", "status": "ok"}]},
            "insufficient_resources": {
                "applies": False, "reason": "齿轮币只增不减,没有消耗型资源"},
            "exit": {"applies": True, "findings": [
                {"text": "删除入口后途中退出不再进入每日关卡",
                 "kind": "consistency", "status": "ok"}]},
            "related_paths": {"applies": True, "findings": [
                {"text": "去掉每日负担是否真的提升留存",
                 "kind": "experience", "method": "发布后第 2 周起对比 7 日回访率",
                 "blocks_stage": False}]},
        },
        "analysis": [
            {"kind": "fact", "detail": "旧档 dayBest 只有当日最佳一个键"},
            {"kind": "correlation",
             "detail": "章节解锁原本依赖每日结算产出的齿轮币"}],
        "invalidated_results": [
            {"id": "V1", "version": "v2", "result": "通过",
             "detail": "每日挑战原型试玩:连续 3 天完成率 62%"}],
        "verification": [
            {"question": "删除每日挑战后成长节奏是否过慢",
             "method": "试玩两章记录解锁间隔", "blocks_stage": False}],
    }
    material.update(over)
    return material


def _meta(**over):
    write = over.pop("write", True)
    sync = over.pop("sync", True)
    meta = {
        "game": "齿轮谜城",
        "module": "每日挑战",
        "date": DATE,
        "qids": ["Q1"],
        "design_path": DESIGN_REL,
        "change_record_path": CHANGE_REL,
        "record_path": DECISION_REL,
        "glossary_path": f"{RECORDS}/glossary.md",
        "version_from": "v2",
        "version_to": "v3",
        "change": "substantive",
        "sync_ref": "GAME_DESIGN v3 / spec-每日挑战 v3",
        "question_start": 5,
        "untouched": [PROJECT_REL, TECH_REL, CODE_REL, SPEC_CHAPTER_REL,
                      SAVE_REL],
        "authorization": {"write": write, "sync": sync},
    }
    meta.update(over)
    return meta


def _existing(project, **over):
    def read(path):
        target = project / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    texts = {path: read(path) for path in
             (SPEC_DAILY_REL, SPEC_GROWTH_REL, SPEC_GUIDE_REL,
              SPEC_CHAPTER_REL, DESIGN_REL, PROJECT_REL, TECH_REL, CODE_REL,
              SAVE_REL, DECISION_REL, CHANGE_REL)}
    texts.update(over)
    return texts


def _plan(project, **over):
    write = over.pop("write", True)
    sync = over.pop("sync", True)
    role_over = over.pop("role_over", {})
    material_over = over.pop("material_over", {})
    meta_over = over.pop("meta_over", {})
    material = _material(**material_over, **over)
    if role_over:
        roles = _roles()
        for role in roles:
            if role["id"] in role_over:
                role.update(role_over[role["id"]])
        material["removal"] = {**material["removal"], "roles": roles}
    return plan_removal(_existing(project),
                        _meta(write=write, sync=sync, **meta_over), material)


def _decided(**over):
    """作用处理答复后:解锁简化保留、存档停写且清理本版不做。"""

    material = _material(**over)
    roles = _roles()
    for role in roles:
        if role["id"] == "unlock":
            role["disposition"] = "simplify"
            role["successor"] = "按关卡数解锁"
            role.pop("options", None)
            role.pop("option_effects", None)
        if role["id"] == "save_data":
            role["disposition"] = "cancel"
            role["scope"] = "not_now"
            role["scope_basis"] = "清理涉及玩家数据,本版不做,未承诺后续版本"
            role.pop("options", None)
            role.pop("option_effects", None)
    material["removal"] = {**material["removal"], "roles": roles,
                           "answers": [{"qid": "Q5", "value": "A",
                                        "basis": "本轮取舍"},
                                       {"qid": "Q6", "value": "A",
                                        "basis": "本轮取舍"}]}
    items = _items()
    for item in items:
        if item["id"] == "unlock_cost":
            item["new_text"] = "- 章节解锁改为按关卡数解锁,不再消耗齿轮币。"
            item["resolution"] = "解锁作用简化保留,不再依赖齿轮币。"
        if item["id"] == "save":
            item["new_text"] = "- 不再写入 dayBest;旧档 dayBest 只读保留,本版不清理。"
            item["resolution"] = "停写并保留读取,清理本版不做。"
    material["design_items"] = items
    return material


def _commit(svc, plan, project, *, purpose="change_sync", resources=None):
    """经受控通道提交计划,再按实际文件回读核对。"""

    instance = _instance(svc, purpose, resources)
    channel = _Channel(svc, instance.token)
    result = apply_removal(plan, channel, _reader(project))
    return result, channel


def _before_texts(project: Path) -> dict[str, str | None]:
    return _existing(project)


def test_lists_original_roles_and_only_asks_undecided_handling() -> None:
    """原作用盘点:八个方面列出作用与关联;只对尚未明确的处理方式提问。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project)
        check(plan["op"] == "removal", f"删减入口标识,实际 {plan.get('op')}")
        check(plan["status"] == "questions",
              f"还有未明确的作用处理时先提问,实际 {plan['status']}")
        check(plan["saved"] is False, "提问阶段不得写入")
        check(plan["request_state"] == "decided", "删除方向已经明确")
        roles = {item["id"]: item for item in plan["removal"]["roles"]}
        check(set(roles) == {"reward_source", "guidance", "unlock", "entry",
                             "tutorial", "content", "save_data",
                             "acceptance_daily"},
              f"八个方面逐项盘点原作用,实际 {sorted(roles)}")
        check(all(item["detail"] for item in roles.values()),
              "每项作用要写明原功能实际承担的作用")
        check(roles["reward_source"]["items"] == ["daily_reward"],
              "每项作用要列出关联的现行设计元素")
        check([item["lane_label"] for item in plan["removal"]["lanes"]]
              == ["奖励来源与成长节奏", "行动引导", "解锁条件", "入口",
                  "教程", "内容", "数据", "验收"],
              f"检查范围与规格字面量一致,实际 "
              f"{[item['lane_label'] for item in plan['removal']['lanes']]}")
        check(roles["reward_source"]["label"] == "转移给已有系统",
              "已明确的作用处理按三类之一记录")
        check(roles["guidance"]["label"] == "更简单方式保留",
              "简化保留的作用处理如实标注")
        check(roles["entry"]["label"] == "一起取消", "取消作用如实标注")
        check([item["id"] for item in plan["questions"]] == ["Q5", "Q6"],
              f"只对尚未明确且影响体验的处理方式提问,实际 "
              f"{[item['id'] for item in plan['questions']]}")
        check([item["source_role"] for item in plan["questions"]]
              == ["unlock", "save_data"],
              "未明确的作用才成为问题")
        texts = " ".join(item["title"] + item["body"]
                         for item in plan["questions"])
        check("是否删除" not in texts and "要不要删" not in texts
              and "是否取消每日挑战" not in texts,
              f"已明确的删除方向不反复询问,实际 {texts}")


def test_dispositions_cover_three_kinds_without_forced_replacement() -> None:
    """三类作用处理:一起取消、转移给已有系统、更简单方式保留;不强制替代品。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project)
        roles = {item["id"]: item for item in plan["removal"]["roles"]}
        check(roles["entry"]["disposition"] == "cancel"
              and roles["entry"]["label"] == "一起取消",
              "入口作用随功能一起取消")
        check(not roles["entry"].get("successor"),
              "一起取消不要求提供替代品")
        check(roles["entry"]["scope_label"].startswith("正式取消"),
              f"取消作用按正式取消记录,实际 {roles['entry']['scope_label']}")
        check(roles["reward_source"]["successor"] == "章节结算"
              and "每章完成结算 21 枚" in roles["reward_source"]["successor_detail"],
              "转移给已有系统要写明承接系统与方式")
        check(roles["guidance"]["successor"] == "章节进度提示",
              "简化保留要写明保留形式")
        check(not any(item.get("source_role") == "entry"
                      for item in plan["questions"]),
              "不因缺少替代品而提问或阻断")
        text = json.dumps(plan, ensure_ascii=False)
        check("每日目标" not in text and "每日任务（替代）" not in text,
              "不自动添加实质相同的同类替代功能")

        equivalent = _plan(project, role_over={
            "guidance": {"successor": "每日目标:每天完成一个目标",
                         "equivalent_replacement": True}})
        check(equivalent["status"] == "incomplete",
              f"实质相同的替代不得当作处理完成,实际 {equivalent['status']}")
        kinds = " ".join(item["kind"] for item in equivalent["unresolved"])
        check("实质相同" in kinds, f"应指出同类替代,实际 {kinds}")
        detail = " ".join(item["detail"] for item in equivalent["unresolved"])
        check("每日挑战" in detail and "每日目标" in detail,
              f"同类替代要写清原功能与替代,实际 {detail}")
        check(equivalent["saved"] is False, "同类替代未处理时不得写入")


def test_residual_dependencies_trace_indirect_and_classify() -> None:
    """残留依赖:追踪间接引用,分为一起取消、需要重新配置与不受影响。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        removal = _plan(project)["removal"]
        residual = removal["residual"]
        check(set(residual["cancel"]) == {"daily_cadence", "menu_entry",
                                          "tutorial_step", "save",
                                          "acceptance_daily"},
              f"随功能一起取消的元素,实际 {sorted(residual['cancel'])}")
        check(set(residual["reconfigure"]) == {"daily_reward", "unlock_cost",
                                               "pool"},
              f"需要重新配置的元素,实际 {sorted(residual['reconfigure'])}")
        check([item["id"] for item in residual["unaffected"]]
              == ["chapter_order"], "无实际依赖的元素列入不受影响")
        check("依赖" in residual["unaffected"][0]["reason"],
              "不受影响要写明核对依据")
        trace = removal["trace"]
        check(trace["daily_reward"]["depth"] == 1,
              "直接引用记直接层")
        check(trace["unlock_cost"]["depth"] == 2
              and trace["unlock_cost"]["path"]
              == ["daily_cadence", "daily_reward", "unlock_cost"],
              f"间接引用要写明经由路径,实际 {trace.get('unlock_cost')}")
        check("间接" in trace["unlock_cost"]["relation"],
              "间接引用按实际关系标注")
        lanes = {item["key"]: item for item in removal["lanes"]}
        check("需要重新配置" in lanes["unlock"]["conclusion"]
              and "unlock_cost" in lanes["unlock"]["conclusion"],
              f"解锁条件方面给出处理结论,实际 {lanes['unlock']['conclusion']}")
        check("需要重新配置" in lanes["reward"]["conclusion"],
              "奖励来源与成长节奏方面给出处理结论")
        check("一起取消" in lanes["acceptance"]["conclusion"],
              "验收方面给出处理结论")
        check("一起取消" in lanes["entry"]["conclusion"],
              "入口方面给出处理结论")

        missing = _plan(project, material_over={"removal": _removal(
            roles=[item for item in _roles() if item["lane"] != "tutorial"])})
        check(missing["status"] == "incomplete",
              f"作用盘点缺项不得判为完成,实际 {missing['status']}")
        kinds = " ".join(item["kind"] for item in missing["unresolved"])
        check("作用盘点缺项" in kinds and "教程" in " ".join(
            item["detail"] for item in missing["unresolved"]),
            f"缺项要写明具体方面,实际 {kinds}")


def test_data_and_entitlements_follow_stage_with_authorization_split() -> None:
    """按真实阶段检查进度、待领资源、存档与权益;处理方案与执行授权分离。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project)
        data = plan["removal"]["data"]
        entries = {item["key"]: item for item in data["entries"]}
        check(set(entries) == {"existing_data", "player_progress",
                               "pending_resources", "entitlements"},
              f"已发布阶段核对存档、玩家进度、待领资源与权益,实际 "
              f"{sorted(entries)}")
        check(entries["existing_data"]["state"] == "exists"
              and "只读保留" in entries["existing_data"]["detail"],
              "存在的存档给出处理方案")
        check(entries["pending_resources"]["state"] == "absent"
              and "不生成处理动作" in entries["pending_resources"]["detail"],
              "核实为不存在的对象不机械讨论补偿")
        check(not any("补偿" in item["title"] + item["body"]
                      for item in plan["questions"]),
              "不追问并不存在的补偿问题")
        pending = data["pending_actions"]
        check([item["action"] for item in pending]
              == ["在实现中停止写入 dayBest", "清理旧档 dayBest 键"],
              f"实际动作单列为待授权,实际 {pending}")
        check(all("需另行授权" in item["note"] for item in pending)
              and all("不执行" in item["note"] for item in pending),
              "处理方案与实际迁移、清理行为保持授权分离")
        check(entries["player_progress"]["item_ids"] == ["save"],
              "数据与权益条目定位到相关设计元素")

        design = _plan(project, material_over={
            "stage": "design_only", "objects": _objects("design_only"),
            "removal": _removal(data_handling={})})
        check(design["removal"]["data"]["entries"] == [],
              "只有设计阶段不讨论并不存在的数据与权益对象")

        missing = _plan(project, material_over={"removal": _removal(
            data_handling={"existing_data": {"plan": ""},
                           "player_progress": {"plan": "保留展示"}})})
        check(missing["status"] == "incomplete",
              f"存在对象缺处理方案不得完成,实际 {missing['status']}")
        check("数据与权益处理方案缺失" in " ".join(
            item["kind"] for item in missing["unresolved"]),
            "缺方案要如实报告")

        unverified = _plan(project, material_over={"removal": _removal(
            data_handling={"existing_data": {"plan": "只读保留"},
                           "player_progress": {},
                           "pending_resources": {"exists": False},
                           "entitlements": {"exists": False}})})
        check(unverified["status"] == "incomplete",
              "存在性未核实的对象不得当作不存在")
        detail = " ".join(item["detail"] for item in unverified["unresolved"])
        check("未核实" in detail and "先核实" in " ".join(
            item["method"] for item in unverified["unresolved"]),
            f"未知对象先核实,实际 {detail}")


def test_scope_separates_permanent_deferral_and_promise() -> None:
    """取消范围:正式取消、当前版本不做与已明确承诺的后续范围不混淆。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project, material_over=_decided())
        roles = {item["id"]: item for item in plan["removal"]["roles"]}
        check(roles["entry"]["scope_label"].startswith("正式取消"),
              f"未提出后续承诺时按正式取消,实际 "
              f"{roles['entry']['scope_label']}")
        check("不自动生成未来任务" in roles["acceptance_daily"]["scope_label"],
              "删除不自动转成未来任务")
        check(roles["save_data"]["scope_label"].startswith("当前版本不做"),
              f"延期处理记当前版本不做,实际 {roles['save_data']['scope_label']}")
        check("尚未承诺后续版本" in roles["save_data"]["scope_label"],
              "延期不得误报为永久取消,也不冒充承诺")
        check(roles["tutorial"]["scope_label"].startswith("已明确承诺的后续范围"),
              f"已承诺事项单独记录,实际 {roles['tutorial']['scope_label']}")
        check("下一版本提供一个不依赖每日挑战的新手引导步骤"
              in roles["tutorial"]["scope_label"]
              and "本轮讨论中开发者已明确承诺"
              in roles["tutorial"]["scope_label"],
              "后续承诺要写明内容与来源")
        record = plan["content"][CHANGE_REL]
        for label in ("正式取消", "当前版本不做", "已明确承诺的后续范围"):
            check(label in record, f"变更记录区分取消范围:{label}")
        section = record.split("## 被删减功能的作用处理")[1]
        line = next(item for item in section.splitlines()
                    if item.startswith("- 当日最佳存档"))
        check("当前版本不做" in line and "正式取消" not in line,
              f"延期不误报为永久取消,实际 {line}")
        check("后续重做每日挑战" not in record and "未来任务：每日挑战" not in record,
              "删除不自动转成未来任务")

        promise = _plan(project, role_over={"tutorial": {"scope_basis": ""}})
        check(promise["status"] == "incomplete",
              f"承诺缺少来源时不得完成,实际 {promise['status']}")
        check("后续承诺缺少来源" in " ".join(
            item["kind"] for item in promise["unresolved"]),
            "缺来源的承诺如实报告")


def test_sync_retires_rules_references_and_acceptance() -> None:
    """获准同步:失效规则、旧入口与旧验收退出;历史与替代关系保留。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        plan = _plan(project, material_over=_decided())
        check(plan["status"] == "planned",
              f"作用处理明确后进入同步计划,实际 {plan['status']}")
        paths = {item["path"] for item in plan["files"]}
        check(paths == {SPEC_DAILY_REL, SPEC_GROWTH_REL, SPEC_GUIDE_REL,
                        DESIGN_REL, CHANGE_REL},
              f"只同步实际受影响文件,实际 {sorted(paths)}")
        daily = plan["content"][SPEC_DAILY_REL]
        check("- 已取消每日挑战模块,不再提供每日关卡与每日结算。" in daily,
              "取消结论写入现行设计")
        check("每天一关,当日仅一次结算。" not in daily.split("## 历史规则")[0],
              "失效规则退出现行版本正文")
        check("## 历史规则" in daily and "替代：- 已取消每日挑战模块" in daily,
              "旧规则进历史段并保留替代关系")
        check("主菜单移除「每日挑战」入口" in daily
              and "主菜单显示「每日挑战」入口。" not in daily.split(
                  "## 历史规则")[0],
              "旧入口退出现行版本")
        check("验收用例随功能取消" in daily
              and "当日重复进行时只保留更优成绩。" not in daily.split(
                  "## 历史规则")[0],
              "旧验收要求退出现行版本")
        growth = plan["content"][SPEC_GROWTH_REL]
        check("章节完成结算齿轮币 21 枚" in growth,
              "转移后的奖励规则写入现有系统")
        check("章节解锁改为按关卡数解锁" in growth,
              "简化保留的解锁规则写入")
        guide = plan["content"][SPEC_GUIDE_REL]
        check("新手教程第 3 步引导玩家进入每日挑战。"
              not in guide.split("## 历史规则")[0],
              "依赖被删功能的教程步骤退出现行版本")
        check("替代：" in guide, "教程旧引用保留替代关系")
        check("需求实质变化" in plan["note"], "同步说明本轮为实质变化")

        result, channel = _commit(svc, plan, project)
        check(result["status"] == "saved",
              f"经真实受控通道应保存成功,实际 {result['status']}")
        check(result["written"][-1] == CHANGE_REL,
              "变更记录最后写入,状态段反映真实结果")
        check(result["states"]["synced"] and not result["states"]["implemented"]
              and not result["states"]["verified"],
              f"状态分档区分已同步与已实现,实际 {result['states']}")

        read = _reader(project)
        verdict = verify_removal(plan, {path: read(path) for path in (
            SPEC_DAILY_REL, SPEC_GROWTH_REL, SPEC_GUIDE_REL,
            SPEC_CHAPTER_REL, DESIGN_REL, CHANGE_REL, PROJECT_REL, TECH_REL,
            CODE_REL, SAVE_REL)})
        check(verdict["ok"], f"回读核对应通过,实际 {verdict['failures']}")
        check(read(CODE_REL) == "// 每日挑战实现:dayBest 每日最佳\n",
              "只授权设计文档时不删除产品代码")
        check(read(SAVE_REL) == SAVE_TEXT, "不修改用户数据")
        check(read(PROJECT_REL) == "# 项目目标\n\n当前版本只做主线 20 关。\n",
              "管理资料保持原样")
        check(read(SPEC_CHAPTER_REL) == CHAPTER_SPEC,
              "无实际依赖的模块保持不变")


def test_record_reports_removal_dispositions_and_scope() -> None:
    """交付与变更记录一致:删掉什么、原因、原作用处理、关联与待验证方法。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        plan = _plan(project, material_over=_decided())
        planned = plan["content"][CHANGE_REL]
        check("已保存：否" in planned and "已同步核心基线：否" in planned,
              "计划内容不预称已保存或已同步")
        result, _channel = _commit(svc, plan, project)
        check(result["status"] == "saved", "记录写入成功")
        record = _reader(project)(CHANGE_REL)
        check("## 被删减功能的作用处理" in record, "含作用处理章节")
        for lane in ("奖励来源与成长节奏", "行动引导", "解锁条件", "入口",
                     "教程", "内容", "数据", "验收"):
            check(lane in record, f"作用处理覆盖方面:{lane}")
        for disposition in ("一起取消", "转移给已有系统", "更简单方式保留"):
            check(disposition in record, f"作用处理表述使用三类用语:{disposition}")
        check("每日挑战" in record and "每日负担重" in record,
              "记录能看清删掉什么与原因")
        check("现有 20 关关卡内容" in record, "记录含保留项")
        check("残留依赖" in record, "记录含残留依赖处理")
        check("间接" in record, "记录含间接引用追踪")
        check("试玩两章记录解锁间隔" in record and "不阻断当前阶段" in record,
              "记录含待验证方法与阻断影响")
        check("原适用版本 v2" in record and "不能证明 v3" in record,
              "旧验证结果标明原适用版本")
        check("设计完成不代表实现或效果完成" in record,
              "设计完成与实际实现效果验证分别报告")
        check("已同步核心基线：是" in record and "已实现：否" in record,
              "状态与真实结果一致")


def test_read_only_and_scope_keep_unauthorized_objects_untouched() -> None:
    """只读与授权边界:未授权只留待同步;越界时不删代码、资源或用户数据。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        before = _before_texts(project)
        read_only = _plan(project, material_over=_decided(), write=False)
        check(read_only["status"] == "read_only",
              f"无写入授权时只读,实际 {read_only['status']}")
        check(read_only["saved"] is False
              and "尚未保存" in read_only["report"],
              "只读时明确尚未保存、尚未同步")
        check(_before_texts(project) == before, "只读讨论不得写入任何文件")

        result, channel = _commit(
            svc, _plan(project, material_over=_decided(), write=False), project)
        check(result["status"] == "read_only" and channel.writes == [],
              "只读计划不经受控通道提交")

        denied, _channel = _commit(
            svc, _plan(project, material_over=_decided()), project,
            purpose="design_discussion")
        check(denied["status"] == "denied",
              f"越界写入应被拒绝,实际 {denied['status']}")
        check(denied["saved"] is False and "未保存" in denied["report"],
              "被拒时如实报告未保存,不换通道重试")
        after = _before_texts(project)
        check(after[CODE_REL] == before[CODE_REL], "产品代码不被删除")
        check(after[SAVE_REL] == before[SAVE_REL], "用户数据不被清理")
        check(after[PROJECT_REL] == before[PROJECT_REL],
              "管理资料保持原状")
        check(after[TECH_REL] == before[TECH_REL], "技术设计保持原状")
        check(after[DESIGN_REL] == before[DESIGN_REL],
              "未获授权时当前有效设计不写入")
        check(after[CHANGE_REL] == before[CHANGE_REL],
              "未获授权时变更记录不写入")


def test_plan_does_not_claim_completion_before_writing() -> None:
    """计划阶段不宣称已保存或已同步;缺位置时不另建一套文档。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project, material_over=_decided())
        check(plan["states"]["saved"] is False
              and plan["states"]["synced"] is False,
              f"计划阶段不得声称已保存/已同步,实际 {plan['states']}")
        check(plan["states"]["adopted"] is True, "已采纳在计划阶段成立")
        check("已保存：否" in plan["content"][CHANGE_REL],
              "计划内容里的状态段如实标未保存")

        no_location = _plan(project, material_over=_decided(),
                            meta_over={"change_record_path": ""})
        check(no_location["status"] == "unauthorized",
              f"缺变更记录位置时不自行另建一套文档,实际 "
              f"{no_location['status']}")
        check("变更记录位置" in no_location["report"],
              "缺位置要如实报告落点问题,不另建文档")
        check(no_location["saved"] is False and no_location["content"] is None,
              "缺位置时不产出可写入内容")


def test_answers_reuse_rounds_and_decisions_records() -> None:
    """作用处理回答沿用票 02/03 的问答与保存路径,不另造记录体系。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project)
        display = run_round(answer_turn(plan, ""))
        for qid in ("Q5", "Q6"):
            check(f"❓ {qid}｜" in display["reply_text"],
                  f"可见回复含固定题目结构 {qid}")
        check("➡️ 我的建议" in display["reply_text"], "每题带建议与理由")
        result = run_round(answer_turn(plan, "Q5 选 A，Q6 选 A"))
        check(result["path"] == "questions",
              f"作用处理问题走同一问答路径,实际 {result['path']}")
        check(result["adopted"].get("Q5", {}).get("value") == "A"
              and result["adopted"].get("Q6", {}).get("value") == "A",
              f"回答对应到决定,实际 {result['adopted']}")
        saved = plan_save(None, result, {
            "record_path": DECISION_REL, "module": "每日挑战",
            "round": 2, "date": DATE, "decider": "开发者",
            "authorization": {"write": True}, "reply": "Q5 选 A，Q6 选 A"})
        check(saved["status"] == "planned",
              f"作用处理回答经票 03 同一保存路径落记录,实际 {saved['status']}")
        check([entry["qid"] for entry in saved["entries"]] == ["Q5", "Q6"],
              f"两项作用处理各成一条决定,实际 {saved['entries']}")

        followed = _plan(project, material_over=_decided())
        check(followed["status"] == "planned",
              "答复回填后进入同步计划")
        check("Q5=A" in followed["change"]["source"],
              "采纳来源记作用处理作答")


def test_removal_reuses_change_flow_seams() -> None:
    """删减沿用票 06 的四项变更说明、阶段核对与既有检查,不另造一套。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project)
        for key in ("change", "stage", "organization", "impact", "record",
                    "files", "states", "version"):
            check(key in plan, f"沿用票 06 计划字段:{key}")
        check(plan["change"]["keep"] == ["现有 20 关关卡内容",
                                         "章节进度与解锁", "本机离线可玩"],
              f"保留项原样沿用,实际 {plan['change']['keep']}")
        check(plan["change"]["reason"] == "每日负担重,与轻量方向冲突",
              "原因原文沿用")
        check("不重复确认是否采纳" in plan["change"]["source"],
              "已明确的删除方向不重复确认")
        check(plan["stage"]["stage"] == "released",
              "沿用票 06 阶段核对")
        check([item["id"] for item in plan["impact"]["must_sync"]]
              == ["daily_cadence", "daily_reward", "menu_entry",
                  "tutorial_step", "pool", "acceptance_daily"],
              f"受影响元素沿用依赖追踪,实际 "
              f"{[item['id'] for item in plan['impact']['must_sync']]}")
        check([item["id"] for item in plan["impact"]["needs_tradeoff"]]
              == ["unlock_cost", "save"],
              "未明确的作用处理进入新增取舍问题")
        check(plan["organization"]["label"] == "模块调整",
              "变更深度沿用票 06 组织方式")
        check(plan["record"]["results"][0]["applies_version"] == "v2",
              "旧验证结果沿用票 06 版本标注")


def test_removal_cli_runs_through_real_gate_channel() -> None:
    """命令行入口:plan 只读、apply 经真实受控通道、verify 回读。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        owner = _instance(svc)
        payload = {"meta": _meta(), "material": _decided()}
        cli = SKILL_DIR / "removal_cli.py"
        planned = subprocess.run(
            [sys.executable, "-B", str(cli), "plan",
             "--project-root", str(project)],
            input=json.dumps(payload), text=True, capture_output=True,
            check=False)
        check(planned.returncode == 0,
              f"plan 应成功,实际 {planned.returncode} {planned.stderr[-200:]}")
        check(json.loads(planned.stdout)["status"] == "planned",
              "plan 输出同步计划")

        applied = subprocess.run(
            [sys.executable, "-B", str(cli), "apply",
             "--project-root", str(project),
             "--runtime-root", str(project.parent / "runtime"),
             "--token", owner.token],
            input=json.dumps(payload), text=True, capture_output=True,
            check=False)
        check(applied.returncode == 0,
              f"apply 应成功,实际 {applied.returncode} {applied.stderr[-200:]}")
        result = json.loads(applied.stdout)
        check(result["status"] == "saved" and result["written"],
              "apply 经受控通道落盘")

        verified = subprocess.run(
            [sys.executable, "-B", str(cli), "verify",
             "--project-root", str(project)],
            input=json.dumps(payload), text=True, capture_output=True,
            check=False)
        check(verified.returncode == 0,
              f"verify 应通过,实际 {verified.stdout[-300:]}")
        check(json.loads(verified.stdout)["ok"] is True, "回读核对通过")

        missing_token = subprocess.run(
            [sys.executable, "-B", str(cli), "apply",
             "--project-root", str(project)],
            input=json.dumps(payload), text=True, capture_output=True,
            check=False)
        check(missing_token.returncode != 0
              and "不自行签发凭据" in missing_token.stdout,
              "缺凭据时不自行签发、不绕过通道")


def test_game_design_entry_points_to_removal_seam() -> None:
    """Game-Design 入口说明删减接缝与纪律,不新增公共入口。"""

    text = LEGACY_DESIGN_ENTRY.read_text(encoding="utf-8")
    for needle in ("removal.py", "removal_impact.py", "removal_cli.py"):
        check(needle in text, f"入口应指向 {needle}")
    for concept in ("一起取消", "转移给已有系统", "更简单方式保留",
                    "正式取消", "当前版本不做", "已明确承诺的后续范围",
                    "残留依赖", "不强制", "另行授权", "不新建公共入口"):
        check(concept in text, f"入口应覆盖概念:{concept}")


def main() -> int:
    return run_theme("完整处理功能删减:原作用、残留依赖与取消范围", (
        test_lists_original_roles_and_only_asks_undecided_handling,
        test_dispositions_cover_three_kinds_without_forced_replacement,
        test_residual_dependencies_trace_indirect_and_classify,
        test_data_and_entitlements_follow_stage_with_authorization_split,
        test_scope_separates_permanent_deferral_and_promise,
        test_sync_retires_rules_references_and_acceptance,
        test_record_reports_removal_dispositions_and_scope,
        test_read_only_and_scope_keep_unauthorized_objects_untouched,
        test_plan_does_not_claim_completion_before_writing,
        test_answers_reuse_rounds_and_decisions_records,
        test_removal_reuses_change_flow_seams,
        test_removal_cli_runs_through_real_gate_channel,
        test_game_design_entry_points_to_removal_seam,
    ), FAILURES)


if __name__ == "__main__":
    sys.exit(main())
