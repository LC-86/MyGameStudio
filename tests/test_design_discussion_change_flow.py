#!/usr/bin/env python3
"""统一设计问答框架票 06:优化已有设计并同步连带影响。

接缝:``plugin/skills/game-design/change_flow.py`` 的 ``plan_change`` /
``apply_change`` / ``verify_change``。固定小型游戏(齿轮谜城)把「每日挑战」
调整为「每周挑战」:提取四项变更说明、沿实际依赖做直接与间接影响分析、
按三种项目阶段核对检查对象、用固定场景推演变化、整理候选与简短变更记录,
并只同步真正受影响的当前设计。期望值来自工单与规格字面量及固定场景语义,
只经公共接口观察行为,不测内部函数。

    python3 -B tests/test_design_discussion_change_flow.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from plugin_package_support import PLUGIN_ROOT, make_checker, run_theme
from runtime_gate_support import GateService

FAILURES, check = make_checker()

SKILL_DIR = PLUGIN_ROOT / "skills" / "game-design"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from change_flow import (  # noqa: E402
    answer_turn, apply_change, plan_change, verify_change,
)
from decisions import plan_save  # noqa: E402
from rounds import run_round  # noqa: E402

RECORDS = "docs/mygamestudio/records"
SPEC_DAILY_REL = f"{RECORDS}/spec-每日挑战.md"
SPEC_GROWTH_REL = f"{RECORDS}/spec-成长资源.md"
SPEC_CHAPTER_REL = f"{RECORDS}/spec-章节.md"
CHANGE_REL = f"{RECORDS}/change-每周挑战.md"
DECISION_REL = f"{RECORDS}/decisions-每日挑战.md"
GLOSSARY_REL = f"{RECORDS}/glossary.md"
DESIGN_REL = "docs/mygamestudio/GAME_DESIGN.md"
PROJECT_REL = "docs/mygamestudio/PROJECT.md"
TECH_REL = "docs/mygamestudio/TECH_DESIGN.md"
CODE_REL = "src/daily.js"
DATE = "2026-09-14"

DAILY_SPEC = """# 每日挑战：模块规格

## 正常规则
- 每天一关,当日仅一次结算。
- 当日关卡由本机日历日加固定种子确定。
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

CHAPTER_SPEC = """# 章节：模块规格

## 正常规则
- 章节按关卡顺序解锁,与每日周期无关。
"""


def _service(root: Path, *, product_write=False):
    project = root / "project"
    (project / "docs/mygamestudio/records").mkdir(parents=True)
    (project / "src").mkdir(parents=True)
    (project / SPEC_DAILY_REL).write_text(DAILY_SPEC, encoding="utf-8")
    (project / SPEC_GROWTH_REL).write_text(GROWTH_SPEC, encoding="utf-8")
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
    """当前有效设计的元素与依赖:每日挑战节奏是变更对象。"""

    return [
        {"id": "cadence", "module": "每日挑战", "lane": "rules",
         "title": "每日挑战节奏", "location": SPEC_DAILY_REL,
         "old_text": "- 每天一关,当日仅一次结算。",
         "new_text": "- 每周一关,当周仅一次结算。",
         "resolution": "按每周周期改写节奏规则。"},
        {"id": "seed", "module": "每日挑战", "lane": "rules",
         "title": "关卡种子规则", "location": SPEC_DAILY_REL,
         "old_text": "- 当日关卡由本机日历日加固定种子确定。",
         "new_text": "- 当周关卡由本机 ISO 周号加固定种子确定。",
         "depends_on": ["cadence"], "resolution": "周期键随节奏改为周。"},
        {"id": "reward", "module": "成长资源", "lane": "growth",
         "title": "周期奖励结算", "location": SPEC_GROWTH_REL,
         "old_text": "- 每日结算齿轮币 3 枚,日上限 3 枚。",
         "depends_on": ["seed"],
         "options": {"A": "每周结算 21 枚,周上限 21 枚",
                     "B": "每周结算 15 枚,周上限 15 枚"},
         "recommendation": "A", "reason": "周总量不变,成长节奏最接近现状。",
         "impact": "影响成长节奏与每周投入。"},
        {"id": "menu", "module": "每日挑战", "lane": "ui",
         "title": "主菜单入口", "location": SPEC_DAILY_REL,
         "old_text": "- 主菜单显示「每日挑战」入口。",
         "new_text": "- 主菜单显示「每周挑战」入口。",
         "depends_on": ["cadence"], "resolution": "入口文案随周期更名。"},
        {"id": "pool", "module": "每日挑战", "lane": "content",
         "title": "关卡池轮换", "location": SPEC_DAILY_REL,
         "old_text": "- 内容：每日关从现有 20 关按日期轮换。",
         "new_text": "- 内容：当周关从现有 20 关按周轮换。",
         "depends_on": ["seed"], "resolution": "沿用现有 20 关,只改轮换周期。"},
        {"id": "save", "module": "每日挑战", "lane": "data",
         "title": "本机存档周期键", "location": SPEC_DAILY_REL,
         "old_text": "- 存档保存当日最佳步数（键 dayBest）。",
         "depends_on": ["cadence"],
         "options": {"A": "新增 weekBest,dayBest 只读保留",
                     "B": "改名 weekBest,旧档不再读取"},
         "recommendation": "A", "reason": "不丢已有进度。",
         "impact": "影响已有存档与进度处理。"},
        {"id": "acceptance_daily", "module": "每日挑战", "lane": "acceptance",
         "title": "每日验收用例", "location": SPEC_DAILY_REL,
         "old_text": "- 验收：当日重复进行时只保留更优成绩。",
         "new_text": "- 验收：当周重复进行时只保留更优成绩。",
         "depends_on": ["cadence"], "resolution": "验收对象随周期改写。"},
        {"id": "chapter", "module": "章节", "lane": "rules",
         "title": "章节进度", "location": SPEC_CHAPTER_REL,
         "old_text": "- 章节按关卡顺序解锁,与每日周期无关。",
         "unaffected_reason": "章节只依赖关卡顺序,与周期无实际关联"},
    ]


def _candidates():
    return [
        {"name": "方案 A:每周结算沿用总量",
         "changes": ["节奏改为每周", "奖励按周结算 21 枚"],
         "keeps": ["章节进度与解锁", "本机离线可玩"],
         "improvement": "降低被迫每日上线的压力",
         "cost": "单次结算变多,周内前段动力略降",
         "evidence": [
             {"kind": "calculation",
              "detail": "每日 3 枚 × 7 = 21 枚/周,总量与现状一致"},
             {"kind": "fact", "detail": "本机存档当前只有 dayBest 一个键"}],
         "chosen": True},
        {"name": "方案 B:只把「每日」字样换成「每周」",
         "changes": ["文案改为每周"], "keeps": ["其余不变"],
         "improvement": "降低被迫每日上线的压力",
         "cost": "机制不变,压力实际没变",
         "evidence": [{"kind": "rename",
                       "detail": "把「每日」字样替换为「每周」,机制不变"}]},
    ]


def _scenarios():
    return {
        "new_player": {"applies": True, "findings": [
            {"text": "新玩家首周即可完成一次周结算", "kind": "consistency",
             "status": "ok"}]},
        "existing_progress": {"applies": True, "findings": [
            {"text": "旧档 dayBest 在方案 A 下只读保留,不丢失",
             "kind": "consistency", "status": "ok"}]},
        "insufficient_resources": {
            "applies": False, "reason": "齿轮币只增不减,没有消耗型资源"},
        "exit": {"applies": True, "findings": [
            {"text": "周内中途退出不结算,下次进入继续当前周",
             "kind": "consistency", "status": "ok"}]},
        "related_paths": {"applies": True, "findings": [
            {"text": "降低每日压力是否真的提升留存", "kind": "experience",
             "method": "发布后第 2 周起对比 7 日回访率", "blocks_stage": False}]},
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


def _material(**over):
    """固定变更场景:每日挑战 → 每周挑战（已由开发者决定方向）。"""

    material = {
        "game": "齿轮谜城",
        "request": {"text": "每日挑战太肝,改成每周挑战",
                    "state": "decided",
                    "decided_direction": "把每日挑战调整为每周挑战"},
        "change": {
            "targets": ["cadence"],
            "target_labels": ["每日挑战节奏"],
            "reason": "每日一局压力大,周中容易断档",
            "improvement": "降低被迫每日上线的压力",
            "keep": ["章节进度与解锁", "本机离线可玩", "现有 20 关内容"],
        },
        "stage": "developed_unreleased",
        "stage_basis": "实现已存在、尚未发布",
        "depth": "module",
        "objects": _objects("developed_unreleased"),
        "design_items": _items(),
        "candidates": _candidates(),
        "scenarios": _scenarios(),
        "core_directions": [
            {"id": "core_loop", "title": "短局循环", "related": True,
             "review": "每周节奏改变单次投入时长,重新核对 3 分钟短局目标"},
            {"id": "art_style", "title": "美术风格", "related": False},
        ],
        "analysis": [
            {"kind": "calculation",
             "detail": "每日 3 枚 × 7 天 = 21 枚/周,与现状总量一致"},
            {"kind": "correlation",
             "detail": "奖励结算依赖种子规则,种子规则依赖挑战节奏"}],
        "invalidated_results": [
            {"id": "V1", "version": "v2", "result": "通过",
             "detail": "每日挑战原型试玩:连续 3 天完成率 62%"}],
        "to_verify": [
            {"question": "每周节奏是否比每日更少压力",
             "method": "发布后第 2 周起对比 7 日回访率",
             "blocks_stage": False}],
        "decided": [{"qid": "Q1", "value": "关卡来源沿用现有 20 关"}],
        "verification": [
            {"question": "每周结算数值是否造成前期囤积",
             "method": "试玩两周记录每周结算时点", "blocks_stage": False}],
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
        "glossary_path": GLOSSARY_REL,
        "version_from": "v2",
        "version_to": "v3",
        "change": "substantive",
        "sync_ref": "GAME_DESIGN v3 / spec-每日挑战 v2",
        "question_start": 5,
        "untouched": [PROJECT_REL, TECH_REL, CODE_REL, SPEC_CHAPTER_REL],
        "authorization": {"write": write, "sync": sync},
    }
    meta.update(over)
    return meta


def _existing(project, **over):
    def read(path):
        target = project / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    texts = {path: read(path) for path in
             (SPEC_DAILY_REL, SPEC_GROWTH_REL, SPEC_CHAPTER_REL, DESIGN_REL,
              PROJECT_REL, TECH_REL, CODE_REL, DECISION_REL, CHANGE_REL,
              GLOSSARY_REL)}
    texts.update(over)
    return texts


def _plan(project, **over):
    write = over.pop("write", True)
    sync = over.pop("sync", True)
    material_over = over.pop("material_over", {})
    meta_over = over.pop("meta_over", {})
    return plan_change(_existing(project),
                       _meta(write=write, sync=sync, **meta_over), _material(
                           **material_over, **over))


def _commit(svc, plan, project, *, purpose="change_sync", resources=None):
    """经受控通道提交计划,再按实际文件回读核对。"""

    instance = _instance(svc, purpose, resources)
    channel = _Channel(svc, instance.token)
    result = apply_change(plan, channel, _reader(project))
    return result, channel


def test_extracts_change_statements_and_does_not_reask_decided() -> None:
    """变更说明与来源:四项齐全;已明确的修改决定不重复询问是否采纳。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project)
        check(plan["status"] == "questions",
              f"有需要取舍的处理方式时先提新增取舍,实际 {plan['status']}")
        check(plan["saved"] is False, "提问阶段不得写入")
        change = plan["change"]
        check(change["targets"] == ["cadence"],
              f"修改对象应为每日挑战节奏,实际 {change['targets']}")
        check(change["reason"] == "每日一局压力大,周中容易断档",
              f"原因原文保留,实际 {change['reason']}")
        check(change["improvement"] == "降低被迫每日上线的压力",
              f"预期改善原文保留,实际 {change['improvement']}")
        check(change["keep"] == ["章节进度与解锁", "本机离线可玩",
                                 "现有 20 关内容"],
              f"保留项应原样列出,实际 {change['keep']}")
        check(plan["request_state"] == "decided", "本轮是已决定的修改请求")
        check("开发者" in change["source"], "采纳来源应记开发者决定")
        check("不重复确认是否采纳" in change["source"],
              "来源应说明不重复确认已明确的修改决定")
        titles = " ".join(item["title"] for item in plan["questions"])
        check("是否采纳" not in titles and "要不要改" not in titles,
              "已明确的修改决定不应重复询问是否修改/是否采纳")
        check([item["source_item"] for item in plan["questions"]]
              == ["reward", "save"],
              "只有真正需要取舍的受影响项才成为问题:"
              f"{[item['source_item'] for item in plan['questions']]}")
        check([item["id"] for item in plan["questions"]] == ["Q5", "Q6"],
              f"编号从当前模块问题组继续,实际 "
              f"{[item['id'] for item in plan['questions']]}")
        check("每日结算齿轮币 3 枚" in plan["questions"][0]["body"],
              "取舍问题要说明失效的旧规则")


def test_traces_direct_and_indirect_impact_by_real_dependency() -> None:
    """影响分析:沿实际依赖追踪间接影响,分三类并保留不受影响项。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        impact = _plan(project)["impact"]
        must = {item["id"]: item for item in impact["must_sync"]}
        check(set(must) == {"cadence", "seed", "menu", "pool",
                            "acceptance_daily"},
              f"必须同步项应为直接与间接受影响规则,实际 {sorted(must)}")
        check(must["cadence"]["depth"] == 0
              and must["cadence"]["relation"] == "变更对象本身",
              "修改对象本身是变更命中点")
        check(must["seed"]["depth"] == 1
              and must["seed"]["relation"]
              == "直接依赖变更对象（cadence）",
              "直接依赖与变更对象本身分开")
        check(must["pool"]["depth"] == 2,
              f"关卡池经种子规则间接受影响,应记深度 2,实际 "
              f"{must['pool']['depth']}")
        check(must["pool"]["relation"] == "间接依赖（经 cadence → seed）",
              f"间接影响要写明经由的实际关系,实际 {must['pool']['relation']}")
        check([item["id"] for item in impact["needs_tradeoff"]]
              == ["reward", "save"], "奖励结算与存档需要用户取舍")
        unreached = {item["id"] for item in impact["unaffected"]}
        check("chapter" in unreached,
              "章节规则与变更无实际依赖,应列入不受影响")
        chapter = next(item for item in impact["unaffected"]
                       if item["id"] == "chapter")
        check("实际关系" in chapter["reason"] or "依赖" in chapter["reason"],
              "不受影响要写明核对依据")
        lanes = {item["key"]: item for item in impact["lanes"]}
        check(set(lanes) == {"rules", "growth", "ui", "content", "data",
                             "acceptance"},
              f"六个方面都要给出结论,实际 {sorted(lanes)}")
        check(lanes["growth"]["must_sync"] == []
              and lanes["growth"]["needs_tradeoff"] == ["reward"],
              "成长资源按实际内容分到需要取舍")
        check("每日挑战节奏" in must["cadence"]["title"],
              "影响条目带可定位的标题")


def test_stage_adapts_checked_objects_for_three_project_stages() -> None:
    """阶段适配:三种阶段核对对象不同;未知不当不存在,不追问无关补偿。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        design = _plan(project, material_over={
            "stage": "design_only", "objects": _objects("design_only")})["stage"]
        check(design["known"] is True and design["label"] == "只有设计，尚未实现",
              f"阶段标签按规格字面量,实际 {design['label']}")
        keys = [item["key"] for item in design["entries"]]
        check("implementation" not in keys and "save_compat" not in keys,
              f"只有设计时不必核对实现与存档兼容,实际 {keys}")
        check(set(keys) == {"rules", "flow", "numbers", "content_list",
                            "acceptance"},
              f"只有设计必查规则/流程/数值/内容清单/验收,实际 {keys}")

        dev = _plan(project)["stage"]
        check(dev["label"] == "已开发，尚未发布", "已开发未发布阶段标签")
        keys = [item["key"] for item in dev["entries"]]
        for key in ("implementation", "ui", "resources", "tests",
                    "existing_data", "save_compat"):
            check(key in keys, f"已开发未发布要核对 {key}")
        check("player_progress" not in keys and "migration" not in keys,
              "已开发未发布不追问玩家进度与迁移")

        released = _plan(project, material_over={
            "stage": "released", "objects": _objects("released")})["stage"]
        check(released["label"] == "已发布，有实际玩家", "已发布阶段标签")
        keys = [item["key"] for item in released["entries"]]
        for key in ("player_progress", "pending_resources", "entitlements",
                    "migration", "release_plan"):
            check(key in keys, f"已发布要核对 {key}")
        absent = {item["key"] for item in released["entries"]
                  if item["state"] == "absent"}
        check("pending_resources" in absent and "entitlements" in absent,
              "核实为不存在的对象如实记为不存在")
        notes = " ".join(item["detail"] for item in released["entries"])
        check("未核实" not in notes,
              "已核实对象不冒充未核实")

        unknown = _plan(project, material_over={
            "stage": "", "objects": {},
            "stage_basis": ""})["stage"]
        check(unknown["known"] is False, "阶段未核实要如实标出")
        check(unknown["missing"] and "阶段未核实" in
              " ".join(item["kind"] for item in unknown["missing"]),
              "阶段未知要有核实要求")
        check(all(item["state"] == "unverified" for item in unknown["entries"]),
              "阶段未知时对象存在性不能当作不存在")
        check("不能当作不存在" in unknown["missing"][0]["detail"],
              "未知不得当作不存在的说明要写清")


def _decided(**over):
    """取舍答复后:奖励与存档按推荐处理,新增决定进入同步计划。"""

    material = _material(**over)
    material.update({
        "request": {"text": "每日挑战太肝,改成每周挑战",
                    "state": "decided",
                    "decided_direction": "把每日挑战调整为每周挑战"},
        "change": {
            "targets": ["cadence"],
            "target_labels": ["每日挑战节奏"],
            "reason": "每日一局压力大,周中容易断档",
            "improvement": "降低被迫每日上线的压力",
            "keep": ["章节进度与解锁", "本机离线可玩", "现有 20 关内容"],
            "answers": [{"qid": "Q5", "value": "A", "basis": "本轮取舍"},
                        {"qid": "Q6", "value": "A", "basis": "本轮取舍"}],
        },
    })
    items = _items()
    for item in items:
        if item["id"] == "reward":
            item["new_text"] = "- 每周结算齿轮币 21 枚,周上限 21 枚。"
            item["resolution"] = "按每周周期结算,总量与现状一致。"
            item.pop("options", None)
        if item["id"] == "save":
            item["new_text"] = ("- 存档保存当周最佳步数（新增键 weekBest,"
                                "dayBest 只读保留）。")
            item["resolution"] = "新增 weekBest,旧档 dayBest 只读保留。"
            item.pop("options", None)
    material["design_items"] = items
    return material


def test_syncs_affected_design_and_keeps_unaffected_content() -> None:
    """获准同步:只改受影响规则与当前设计,未受影响的现行内容保持原样。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        plan = _plan(project, material_over=_decided())
        check(plan["status"] == "planned",
              f"取舍明确后进入同步计划,实际 {plan['status']}")
        paths = {item["path"] for item in plan["files"]}
        check(paths == {SPEC_DAILY_REL, SPEC_GROWTH_REL, DESIGN_REL,
                        CHANGE_REL},
              f"只同步实际受影响文件,实际 {sorted(paths)}")
        spec = plan["content"][SPEC_DAILY_REL]
        check("- 每周一关,当周仅一次结算。" in spec,
              "新规则写入当前有效设计")
        check("每天一关,当日仅一次结算。" not in spec.split(
            "## 历史规则")[0],
            "失效规则退出现行版本正文")
        check("## 历史规则" in spec and "替代：- 每周一关" in spec,
              "旧规则进历史段并保留替代关系")
        check("- 存档保存当周最佳步数（新增键 weekBest,dayBest 只读保留）。"
              in spec, "受影响的数据规则同步更新")
        check("# 每日挑战：模块规格" in spec, "沿用现有规格位置,不重造文档")

        result, _channel = _commit(svc, plan, project)
        check(result["status"] == "saved",
              f"经真实受控通道应保存成功,实际 {result['status']}")
        check(result["states"]["saved"] and result["states"]["synced"],
              f"状态分档应区分已保存与已同步,实际 {result['states']}")
        check(result["states"]["implemented"] is False
              and result["states"]["verified"] is False,
              "缺少实际运行或效果证据时不得称已实现或已验证")

        read = _reader(project)
        verdict = verify_change(plan, {path: read(path) for path in (
            SPEC_DAILY_REL, SPEC_GROWTH_REL, SPEC_CHAPTER_REL, DESIGN_REL,
            CHANGE_REL, PROJECT_REL, TECH_REL, CODE_REL)})
        check(verdict["ok"], f"回读核对应通过,实际 {verdict['failures']}")
        record = read(CHANGE_REL)
        for needle in ("## 目标与原因", "## 旧设计到新设计", "## 影响范围",
                       "## 阶段与对象检查", "## 场景推演", "## 待验证",
                       "## 旧验证结果", "## 状态"):
            check(needle in record, f"变更记录含 {needle}")
        check("每日一局压力大,周中容易断档" in record, "变更记录含原因")
        check("降低被迫每日上线的压力" in record, "变更记录含预期改善")
        check("章节进度与解锁" in record, "变更记录含保留项")
        check("Q5=A" in record and "Q6=A" in record,
              "变更记录含取舍问题作答与采纳来源")
        check("原适用版本 v2" in record,
              "旧验证结果标明原适用版本")
        check("不能证明 v3" in record,
              "旧验证结果不能当作新方案已通过")
        check("已同步核心基线：是" in record and "已实现：否" in record,
              "变更记录状态与真实结果一致")
        check("项目目标" in read(PROJECT_REL)
              and read(PROJECT_REL) == (project / PROJECT_REL).read_text(
                  encoding="utf-8"),
              "未受影响的现行资料保持原样")
        check(read(CODE_REL) == "// 每日挑战实现:dayBest 每日最佳\n",
              "只授权设计文档修改时产品代码保持原样")


def test_candidates_explain_change_keep_improvement_cost_and_evidence() -> None:
    """候选说明改什么、保留什么、预期改善与代价;换名不算改善证据。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        plan = _plan(project, material_over=_decided())
        candidates = plan["record"]["candidates"]
        chosen = next(item for item in candidates if item["choice"] == "采纳")
        check(chosen["name"] == "方案 A:每周结算沿用总量", "采纳的候选原样列出")
        check(chosen["changes"] == ["节奏改为每周", "奖励按周结算 21 枚"],
              f"候选要说明改什么,实际 {chosen['changes']}")
        check("章节进度与解锁" in chosen["keeps"], "候选要说明保留什么")
        check(chosen["improvement"] == "降低被迫每日上线的压力",
              "候选要说明预期改善")
        check(chosen["cost"] == "单次结算变多,周内前段动力略降",
              "候选要说明代价")
        check("每日 3 枚 × 7 = 21 枚/周" in chosen["evidence_summary"],
              "改善要有可核对的计算或事实依据")
        rename = next(item for item in candidates
                      if item["name"].startswith("方案 B"))
        check(rename["choice"] == "未采纳", "只换名的方案如实标为未采纳")
        check(rename["evidence_summary"] ==
              "仅换名或转移复杂度,不构成改善证据,只记为改了什么",
              f"换名或转移复杂度不算改善证据,实际 {rename['evidence_summary']}")

        renamed = _decided(candidates=[{
            "name": "方案 C:改叫每周挑战", "changes": ["文案改名"],
            "keeps": ["全部现状"], "improvement": "降低压力", "cost": "无",
            "evidence": [{"kind": "rename", "detail": "把每日改名每周"}],
            "chosen": True}])
        blocked = _plan(project, material_over=renamed)
        check(blocked["status"] == "incomplete",
              f"只换名的方案不得当作问题已解决,实际 {blocked['status']}")
        kinds = " ".join(item["kind"] for item in blocked["unresolved"])
        check("改善证据不足" in kinds,
              f"应指出改善证据不足,实际 {kinds}")
        check(blocked["saved"] is False, "证据不足时不得写入")


def test_scenario_walkthrough_separates_consistency_from_experience() -> None:
    """场景推演:覆盖适用场景,自洽性与实际体验改善分开标注。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        record = _plan(project, material_over=_decided())["record"]
        details = {item["label"]: item["detail"]
                   for item in record["walkthrough"]}
        check(set(details) == {"新玩家", "已有进度", "资源不足", "退出",
                               "相关路径"},
              f"适用场景都要推演,实际 {sorted(details)}")
        check("不适用" in details["资源不足"] and "只增不减" in details["资源不足"],
              "不适用场景要写明理由")
        check("（自洽性）" in details["已有进度"],
              f"数值/流程自洽单独标注,实际 {details['已有进度']}")
        check("（体验改善）" in details["相关路径"]
              and "对比 7 日回访率" in details["相关路径"],
              f"体验改善要有方法与阻断影响,实际 {details['相关路径']}")
        check("自洽" not in details["相关路径"],
              "体验改善不作为自洽性通过")
        verify = record["verify"]
        check(any("试玩两周" in item["method"] for item in verify),
              "需要试玩时保留具体方法与判定")
        check(all("blocks_stage" in item for item in verify),
              "待验证要说明是否阻断当前阶段")


def test_depth_organizes_work_and_keeps_valid_decisions() -> None:
    """变更深度:模块调整用当前模块问题组;方向变化只重审相关核心方向。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        module = _plan(project)["organization"]
        check(module["depth"] == "module" and module["label"] == "模块调整",
              f"默认按模块调整组织,实际 {module['label']}")
        check("当前模块" in module["note"], "模块调整用当前模块问题组")

        structural = _plan(project, material_over={
            "depth": "structural"})["organization"]
        check(structural["label"] == "结构性修改"
              and set(structural["modules"]) == {"每日挑战", "成长资源"},
              f"结构性修改列出受影响模块,实际 {structural['modules']}")
        check(structural["verification"],
              "结构性修改按需提出验证")

        directional = _plan(project, material_over={
            "depth": "directional"})["organization"]["directions"]
        check(directional["applies"] is True, "方向性变化标记为需重审方向")
        check([item["id"] for item in directional["reviewed"]] == ["core_loop"],
              "只重审与变更相关的核心方向")
        check([item["id"] for item in directional["kept"]] == ["art_style"],
              "其余有效决定继续保留")

        missing = _plan(project, material_over={
            "depth": "directional",
            "core_directions": [{"id": "core_loop", "title": "短局循环",
                                 "related": True}]})
        check(missing["status"] == "incomplete",
              f"相关核心方向未审视时不得完成,实际 {missing['status']}")
        check("核心方向未审视" in " ".join(
            item["kind"] for item in missing["unresolved"]),
            "缺审视结论要如实报告")

        tweak = _plan(project, material_over={
            "depth": "local_tweak",
            "verification": [{"question": "文案是否清楚",
                              "method": "读一遍", "blocks_stage": False}]})
        check(tweak["organization"]["label"] == "局部明确微调",
              "局部微调走简短流程")
        check(tweak["record"]["verify"] == [],
              "局部微调不强行附加无关验证要求")


def _before_texts(project: Path) -> dict[str, str | None]:
    texts: dict[str, str | None] = {}
    for path in (SPEC_DAILY_REL, SPEC_GROWTH_REL, SPEC_CHAPTER_REL,
                 DESIGN_REL, PROJECT_REL, TECH_REL, CODE_REL, DECISION_REL,
                 CHANGE_REL):
        target = project / path
        texts[path] = (target.read_text(encoding="utf-8")
                       if target.is_file() else None)
    return texts


def test_read_only_and_scope_keep_product_untouched() -> None:
    """只读与授权边界:未授权只留待同步项;越界写入不改产品代码与外部系统。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        before = _before_texts(project)
        read_only = _plan(project, material_over=_decided(), write=False)
        check(read_only["status"] == "read_only",
              f"无写入授权时只读,实际 {read_only['status']}")
        check(read_only["saved"] is False and "尚未保存" in read_only["report"],
              "只读时明确尚未保存、尚未同步")
        check(_before_texts(project) == before,
              "只读讨论不得写入任何文件")

        result, channel = _commit(
            svc, _plan(project, material_over=_decided(), write=False), project)
        check(result["status"] == "read_only" and channel.writes == [],
              "只读计划不经受控通道提交")

        result, _channel = _commit(
            svc, _plan(project, material_over=_decided()), project,
            purpose="design_discussion")
        check(result["status"] == "denied",
              f"越界写入应被拒绝,实际 {result['status']}")
        check(result["saved"] is False and "未保存" in result["report"],
              "被拒时如实报告未保存,不换通道重试")
        check(result["report"].count("已同步核心基线") == 0
              or "未完成" in result["report"],
              "部分写入时要如实说明本轮变更未完成")
        after = _before_texts(project)
        check(after[CODE_REL] == before[CODE_REL], "产品代码保持原状")
        check(after[PROJECT_REL] == before[PROJECT_REL],
              "管理资料保持原状")
        check(after[TECH_REL] == before[TECH_REL],
              "技术设计保持原状")
        check(after[DESIGN_REL] == before[DESIGN_REL],
              "未获授权时当前有效设计不写入")
        check(after[CHANGE_REL] == before[CHANGE_REL],
              "未获授权时变更记录不写入")
        check(not (project / "data").exists(),
              "未授权数据目录不发生变更")


def test_three_stages_and_directional_fixture_cover_contract() -> None:
    """验收夹具:三种阶段 + 一次方向调整,核对依赖、保留项、同步范围与状态。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        for stage in ("design_only", "developed_unreleased", "released"):
            plan = _plan(project, material_over={
                "stage": stage, "objects": _objects(stage),
                "depth": "directional", "request": {
                    "text": "整体方向改为轻量休闲",
                    "state": "decided",
                    "decided_direction": "把节奏从每日改为每周"}})
            check(plan["stage"]["known"] is True,
                  f"{stage} 阶段应被识别")
            check(plan["change"]["keep"] == ["章节进度与解锁", "本机离线可玩",
                                             "现有 20 关内容"],
                  f"{stage} 下保留项不变: {plan['change']['keep']}")
            check([item["id"] for item in plan["impact"]["must_sync"]]
                  == ["cadence", "seed", "menu", "pool", "acceptance_daily"],
                  f"{stage} 下依赖分析结果一致")
            check(plan["organization"]["directions"]["reviewed"],
                  f"{stage} 下方向调整重审相关核心方向")
            check(plan["states"]["implemented"] is False
                  and plan["states"]["verified"] is False,
                  f"{stage} 下未经证据不标已实现/已验证")

        final = _plan(project, material_over=_decided())
        result, _channel = _commit(svc, final, project)
        check(set(result["written"]) == {SPEC_DAILY_REL, SPEC_GROWTH_REL,
                                         DESIGN_REL, CHANGE_REL},
              f"同步范围只含受影响文件,实际 {result['written']}")
        check(result["written"][-1] == CHANGE_REL,
              "变更记录最后写入,状态段反映真实结果")
        check(result["states"]["adopted"] and result["states"]["saved"]
              and result["states"]["synced"],
              "状态区分已采纳/已保存/已同步")
        after = _before_texts(project)
        check(after[PROJECT_REL] and after[TECH_REL] and after[CODE_REL],
              "只授权设计文档修改时产品代码、管理资料与技术设计保持原状")


def test_cli_runs_through_real_gate_channel() -> None:
    """命令行入口:plan 只读、apply 经真实受控通道、verify 回读。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        owner = _instance(svc)
        payload = {"meta": _meta(), "material": _decided()}
        cli = SKILL_DIR / "change_flow_cli.py"
        planned = subprocess.run(
            [sys.executable, "-B", str(cli), "plan",
             "--project-root", str(project)],
            input=json.dumps(payload), text=True, capture_output=True,
            check=False)
        check(planned.returncode == 0,
              f"plan 应成功,实际 {planned.returncode} {planned.stderr[-200:]}")
        plan = json.loads(planned.stdout)
        check(plan["status"] == "planned", "plan 输出同步计划")

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


def test_game_design_entry_points_to_change_seam() -> None:
    """Game-Design 入口说明变更接缝与纪律,不改公共入口集合。"""

    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("change_flow.py", "change_impact.py", "change_input.py",
                   "change_render.py", "change_report.py",
                   "change_flow_cli.py"):
        check(needle in text, f"入口应指向 {needle}")
    for concept in ("修改对象", "预期改善", "保留", "必须同步",
                    "需要开发者取舍", "不受影响", "只有设计",
                    "已开发，尚未发布", "已发布，有实际玩家", "变更记录",
                    "换名", "不新建公共入口"):
        check(concept in text, f"入口应覆盖概念:{concept}")


def test_answers_reuse_rounds_and_decisions_records() -> None:
    """取舍回答沿用票 02/03 的问答与记录路径,不另造一套记录体系。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project)
        display = run_round(answer_turn(plan, ""))
        for qid in ("Q5", "Q6"):
            check(f"❓ {qid}｜" in display["reply_text"],
                  f"可见回复含固定题目结构 {qid}")
        check("➡️ 我的建议" in display["reply_text"], "每题带建议与理由")
        check("Q5" in display["shown_ids"] and "Q6" in display["shown_ids"],
              "取舍问题在同一轮展示")
        result = run_round(answer_turn(plan, "Q5 选 A，Q6 选 A"))
        check(result["path"] == "questions",
              f"取舍问题走同一问答路径,实际 {result['path']}")
        check(result["adopted"].get("Q5", {}).get("value") == "A",
              f"回答对应到决定,实际 {result['adopted']}")
        check(result["adopted"].get("Q6", {}).get("value") == "A",
              "两项取舍都对应到决定")
        check(result["module"] == "每日挑战", "沿用同一模块")
        check("✅ 已确定" in result["reply_text"], "给出已确定结果")
        check(not any(qid in result["pending"] for qid in ("Q5", "Q6")),
              "已回答的取舍不留在待讨论")
        saved = plan_save(None, result, {
            "record_path": DECISION_REL, "module": "每日挑战",
            "round": 2, "date": DATE, "decider": "开发者",
            "authorization": {"write": True}, "reply": "Q5 选 A，Q6 选 A"})
        check(saved["status"] == "planned",
              f"取舍回答经票 03 同一保存路径落记录,实际 {saved['status']}")
        check([entry["qid"] for entry in saved["entries"]] == ["Q5", "Q6"],
              f"两项取舍各成一条决定,实际 {saved['entries']}")
        check(all(entry["impact"] for entry in saved["entries"]),
              "决定记录保留影响说明")

        answered = _decided()
        for item in answered["design_items"]:
            if item["id"] == "reward":
                item["question_id"] = "Q5"
                item["new_text"] = ""
                item["resolution"] = ""
                item["options"] = {"A": "每周结算 21 枚,周上限 21 枚",
                                   "B": "每周结算 15 枚,周上限 15 枚"}
            if item["id"] == "save":
                item["question_id"] = "Q6"
                item["new_text"] = ""
                item["resolution"] = ""
                item["options"] = {"A": "新增 weekBest,dayBest 只读保留",
                                   "B": "改名 weekBest,旧档不再读取"}
        followed = _plan(project, material_over=answered)
        check(followed["status"] == "planned",
              f"答复回填后进入同步计划,实际 {followed['status']}")
        growth = followed["content"][SPEC_GROWTH_REL]
        check("- 每周结算 21 枚,周上限 21 枚。" in growth,
              f"选中选项成为新的当前规则,实际 {growth[-300:]}")
        daily = followed["content"][SPEC_DAILY_REL]
        check("新增 weekBest,dayBest 只读保留" in daily,
              "存档处理按选中的选项写入")
        check("Q5" in followed["change"]["source"]
              and "A" in followed["change"]["source"],
              "采纳来源记取舍问题作答")


def test_plan_does_not_claim_sync_before_writing() -> None:
    """计划阶段不宣称已保存或已同步:状态只在写入后按实际结果分档。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project, material_over=_decided())
        check(plan["states"]["saved"] is False
              and plan["states"]["synced"] is False,
              f"计划阶段不得声称已保存/已同步,实际 {plan['states']}")
        check(plan["states"]["adopted"] is True, "已采纳在计划阶段成立")
        check("已保存：否" in plan["content"][CHANGE_REL],
              "计划内容里的状态段如实标未保存")

        result, _channel = _commit(
            _svc, plan, project,
            purpose="design_discussion")
        check(result["saved"] is False, "未获授权时不得保存")
        check(result["states"]["saved"] is False,
              "被拒后状态仍为未保存")


def test_old_validation_result_keeps_original_version() -> None:
    """旧验证结果标明原适用版本;未标明的旧结果会被回读核对检出。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        plan = _plan(project, material_over=_decided())
        record = plan["record"]
        check(record["results"][0]["applies_version"] == "v2",
              "旧验证结果按原适用版本登记")
        check("不能证明 v3" in record["results"][0]["note"],
              "旧验证结果不能证明新方案已通过")
        check("原适用版本 v2" in plan["content"][CHANGE_REL],
              "变更记录写明原适用版本")

        blanked = dict(plan["content"])
        blanked[CHANGE_REL] = blanked[CHANGE_REL].replace(
            "原适用版本 v2", "原适用版本")
        read = _reader(project)

        def fake(path):
            if path in blanked:
                return blanked[path]
            return read(path)

        verdict = verify_change(plan, {
            path: fake(path) for path in (SPEC_DAILY_REL, SPEC_GROWTH_REL,
                                          DESIGN_REL, CHANGE_REL)})
        check(not verdict["ok"], "缺原适用版本的旧结果不得判为通过")
        check(any("原适用版本" in item for item in verdict["failures"]),
              f"应报告缺少原适用版本,实际 {verdict['failures']}")


def test_removal_disposition_seam_is_carried_through() -> None:
    """删减类变更的作用处理透传(第 07 票深化),不在本票展开。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        items = _items()
        for item in items:
            if item["id"] == "reward":
                item.update({
                    "new_text": "- 删除每日结算。",
                    "resolution": "奖励结算一起取消,改由章节结算承接。",
                    "disposition": "transfer",
                    "disposition_detail": "奖励作用转移给章节结算"})
                item.pop("options", None)
            if item["id"] == "save":
                item["new_text"] = "- 删除 dayBest。"
                item["resolution"] = "旧档键停用但保留读取。"
                item.pop("options", None)
        material = _decided()
        material["design_items"] = items
        material["change"]["answers"] = []
        plan = _plan(project, material_over=material)
        check(plan["status"] == "planned",
              f"标注作用处理后不再列为待取舍,实际 {plan['status']}")
        dispositions = plan["record"]["dispositions"]
        check(dispositions == [{"id": "reward", "title": "周期奖励结算",
                                "kind": "transfer",
                                "label": "转移给已有系统",
                                "detail": "奖励作用转移给章节结算"}],
              f"作用处理原样带入记录,实际 {dispositions}")
        check("## 被删减功能的作用处理" in plan["content"][CHANGE_REL],
              "变更记录含作用处理段")
        check("转移给已有系统" in plan["content"][CHANGE_REL],
              "作用处理按取消/转移/简化保留表述")


def test_stale_rule_not_found_blocks_sync() -> None:
    """现行设计里找不到的旧规则不得静默通过:先核对实际内容再决定。"""

    with tempfile.TemporaryDirectory() as tmp:
        _svc, project = _service(Path(tmp))
        stale = _decided()
        for item in stale["design_items"]:
            if item["id"] == "menu":
                item["old_text"] = "- 主菜单显示「挑战」入口。"  # 实际不存在
        plan = _plan(project, material_over=stale)
        check(plan["status"] == "incomplete",
              f"旧规则定位不到时不得直接同步,实际 {plan['status']}")
        check(any(item["kind"] == "旧规则未定位"
                  for item in plan["unresolved"]),
              f"应报告旧规则未定位,实际 {plan['unresolved']}")
        check(plan["saved"] is False and plan["content"] is None,
              "定位失败时不产出可写入内容")


def main() -> int:
    return run_theme("已有设计变更:影响、阶段与同步", (
        test_extracts_change_statements_and_does_not_reask_decided,
        test_traces_direct_and_indirect_impact_by_real_dependency,
        test_stage_adapts_checked_objects_for_three_project_stages,
        test_syncs_affected_design_and_keeps_unaffected_content,
        test_candidates_explain_change_keep_improvement_cost_and_evidence,
        test_scenario_walkthrough_separates_consistency_from_experience,
        test_depth_organizes_work_and_keeps_valid_decisions,
        test_read_only_and_scope_keep_product_untouched,
        test_three_stages_and_directional_fixture_cover_contract,
        test_answers_reuse_rounds_and_decisions_records,
        test_plan_does_not_claim_sync_before_writing,
        test_old_validation_result_keeps_original_version,
        test_removal_disposition_seam_is_carried_through,
        test_stale_rule_not_found_blocks_sync,
        test_cli_runs_through_real_gate_channel,
        test_game_design_entry_points_to_change_seam,
    ), FAILURES)


if __name__ == "__main__":
    sys.exit(main())
