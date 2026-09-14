#!/usr/bin/env python3
"""统一设计问答框架票 05:从游戏想法形成完整设计文档。

接缝:``plugin/skills/game-design/coverage_map.py``(十二领域覆盖地图与范围/阶段)、
``journey.py``(玩家视角流程核对与资源/解锁矛盾)、``full_design.py``(四类
交付组织、交接标准与受控写入)。固定小型游戏场景(齿轮谜城每日挑战)经票 02
``rounds.run_round``、票 03 ``decisions``、票 04 ``spec_draft`` 真实接缝走
完整流程,再核对覆盖地图、四类交付物、交接标准、矛盾与缺口检出。期望值来自
工单与规格字面量,只经公共接口观察行为,不测内部函数。

    python3 -B tests/test_design_discussion_full_design.py
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

from checks import begin, record_read, remember, reuse  # noqa: E402
from coverage_map import DOMAINS, build_map, stage_status  # noqa: E402
from decision_records import sha256_text  # noqa: E402
from decisions import apply_save, plan_save  # noqa: E402
from full_design import (  # noqa: E402
    apply_delivery, plan_delivery, verify_delivery,
)
from journey import find_contradictions, walkthrough  # noqa: E402
from rounds import run_round  # noqa: E402
from spec_draft import apply_handoff, plan_handoff  # noqa: E402

RECORD_REL = "docs/mygamestudio/records/decisions-每日挑战.md"
SPEC_REL = "docs/mygamestudio/records/spec-每日挑战.md"
EXIT_SPEC_REL = "docs/mygamestudio/records/spec-退出重进.md"
PENDING_REL = "docs/mygamestudio/records/delivery-pending.md"
GLOSSARY_REL = "docs/mygamestudio/records/glossary.md"
DESIGN_REL = "docs/mygamestudio/GAME_DESIGN.md"
CONTENT_REL = "docs/mygamestudio/CONTENT_PRODUCTION.md"
VERSION_REL = "docs/mygamestudio/VERSION_PLAN.md"
PROJECT_REL = "docs/mygamestudio/PROJECT.md"
TECH_REL = "docs/mygamestudio/TECH_DESIGN.md"
DATE = "2026-09-14"
TEST_ANSWER = "（测试回答,非真实开发者决定）"

DOMAIN_KEYS = (
    "project", "appeal", "core_play", "journey", "systems", "growth",
    "content", "ui", "presentation", "release", "tech", "version",
)


def _service(root: Path):
    """临时项目 + 真实受控通道服务(设计角色可写记录目录与成稿交付)。"""

    project = root / "project"
    (project / "docs/mygamestudio/records").mkdir(parents=True)
    (project / DESIGN_REL).write_text(
        "# 齿轮谜城:当前游戏需求与设计\n\n基线版本:v2。\n", encoding="utf-8")
    (project / PROJECT_REL).write_text(
        "# 项目目标\n\n当前版本只做主线 20 关,不含联网能力。\n",
        encoding="utf-8")
    (project / TECH_REL).write_text(
        "# 技术设计\n\n存档为本地 JSON,无联网功能。\n", encoding="utf-8")
    (project / CONTENT_REL).write_text(
        "# 齿轮谜城:内容与视听制作需求\n\n"
        "既有说明：音效全部沿用现有素材,不新增录音。\n", encoding="utf-8")
    (project / "docs/mygamestudio/CONFIG.md").write_text(
        "# 齿轮谜城:协作配置\n\n## 任务来源\n\n- 后端：local-markdown\n"
        "- 当前位置：work/\n\n## 文档映射\n\n"
        "| 内容 | 当前权威位置 | 维护角色 |\n| --- | --- | --- |\n"
        f"| 项目目标与范围 | {PROJECT_REL} | 制作统筹 |\n"
        f"| 游戏需求与设计 | {DESIGN_REL} | 方案设计 |\n"
        f"| 技术设计 | {TECH_REL} | 制作实现 |\n"
        f"| 术语、ADR 与历史 | {GLOSSARY_REL} | 对应专业角色 |\n",
        encoding="utf-8")
    svc = GateService(root / "runtime")
    svc.init_policy(
        project_root=project,
        roles={"design": ["docs/mygamestudio/records/**", DESIGN_REL,
                          CONTENT_REL, VERSION_REL]},
        purposes={
            "design_discussion": ["docs/mygamestudio/records/**"],
            "spec_sync": ["docs/mygamestudio/records/**", DESIGN_REL,
                          CONTENT_REL, VERSION_REL],
        },
    )
    return svc, project


class _Channel:
    """测试用通道适配:与 mgs-gate 提交同一条 GateService 受控写入路径。"""

    def __init__(self, svc, token):
        self.svc = svc
        self.token = token
        self.writes = []
        self.scopes = []

    def scope(self):
        result = self.svc.scope(self.token)
        self.scopes.append(result)
        return result

    def write(self, path, content, expected_sha256=None, note=None):
        self.writes.append({"path": path, "expected_sha256": expected_sha256})
        return self.svc.write(self.token, path, content,
                              expected_sha256=expected_sha256, note=note)


def _reader(project: Path):
    def read(path: str):
        target = project / path
        return target.read_text(encoding="utf-8") if target.is_file() else None
    return read


def _instance(svc, purpose="design_discussion", resources=None):
    return svc.create_instance(
        role="design", task="G02", purpose=purpose,
        resources=list(resources or ["docs/mygamestudio/records/**"]),
        ttl_seconds=1800)


def _handoff_token(svc):
    return _instance(
        svc, purpose="spec_sync",
        resources=["docs/mygamestudio/records/**", DESIGN_REL, CONTENT_REL,
                   VERSION_REL]).token


def _questions():
    return [
        {"id": "Q1", "title": "关卡来源", "body": "每日关从哪来?",
         "options": {"A": "从现有 20 关按日期抽取", "B": "每日生成新关"},
         "recommendation": "A", "reason": "沿用现有内容最省制作。",
         "module": "每日挑战", "depends_on": [],
         "impact": "决定每日关的复用方式;记录规则依赖它。"},
        {"id": "Q2", "title": "与章节关系", "body": "和章节什么关系?",
         "options": {"A": "替代章节", "B": "与章节并存"},
         "recommendation": "B", "reason": "并存不破坏已有关卡。",
         "module": "每日挑战", "depends_on": [],
         "impact": "决定主菜单入口数量。"},
        {"id": "Q3", "title": "每日身份", "body": "如何确定每日关?",
         "options": {"A": "本机日历日加固定种子", "B": "联网对时"},
         "recommendation": "A", "reason": "离线可玩。",
         "module": "每日挑战", "depends_on": [],
         "impact": "影响离线与公平性。"},
        {"id": "Q4", "title": "记录", "body": "每日最佳成绩如何记录?",
         "options": {"A": "只保留本机当日最佳步数", "B": "联网排行榜"},
         "recommendation": "A", "reason": "先不引入联网。",
         "module": "每日挑战", "depends_on": ["Q3"],
         "impact": "影响本机存档结构。"},
    ]


def _turn(reply, *, round_no=1, settled=None, shown=None):
    return {
        "request": "想给游戏加每日挑战模式,每天一关。",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "round": round_no,
        "current_design": {"exists": True, "covers_request": False},
        "questions": _questions(),
        "shown": list(shown or ["Q1", "Q2", "Q3"]),
        "settled": dict(settled or {}),
        "user_reply": reply,
    }


def _record_meta(*, round_no=1, reply=""):
    return {"record_path": RECORD_REL, "module": "每日挑战", "round": round_no,
            "date": DATE, "decider": "开发者",
            "authorization": {"write": True}, "reply": reply}


def _save_decisions(save_channel, read, replies):
    """票 02/03 真实接缝:明确标注的测试回答 → 实际落盘的决定记录。

    回答文本带 ``TEST_ANSWER`` 标注,便于在实际记录与产物中区分验收用测试
    回答和真实开发者决定。
    """

    settled = {}
    for index, (reply, shown) in enumerate(replies, start=1):
        reply = f"{TEST_ANSWER}{reply}"
        result = run_round(_turn(reply, round_no=index, settled=dict(settled),
                                 shown=list(shown)))
        applied = apply_save(
            plan_save(read(RECORD_REL), result,
                      _record_meta(round_no=index, reply=reply)),
            save_channel, read)
        check(applied["status"] == "saved",
              f"固定场景第 {index} 轮决定应实际落盘,实际 {applied['status']}")
        settled.update({qid: item["value"]
                        for qid, item in result["adopted"].items()})
    return settled


def _spec_sections():
    """票 04 固定模块(每日挑战)的九类规格内容,全部为具体规则与数值。"""

    return {
        "purpose": {"content": "让玩家每天用一次短局回到游戏;复用已有关卡,"
                               "不新增内容制作。", "sources": ["Q1"]},
        "participants": {"content": "玩家、每日关卡、每日种子、本机当日最佳记录;"
                                    "章节进度不受影响。", "sources": ["Q2"]},
        "triggers": {"content": "玩家从主菜单进入每日挑战时生效;当日关卡由"
                                "本机日历日加固定种子确定。", "sources": ["Q3"]},
        "rules": {"content": "选择本机日期对应关卡 → 完成一局 → 按步数结算 → "
                             "更新当日最佳;每日只保留一个最佳值。",
                  "sources": ["Q1", "Q2"]},
        "boundaries": {"content": "同日重复进行:只有更优成绩覆盖最佳;离线:"
                                  "直接使用本机日期;跨日:旧日最佳不再更新;"
                                  "失败或中途退出:不记录最佳。",
                       "sources": ["Q1"]},
        "numbers": {
            "settled": [
                {"name": "每日关卡数量", "value": "1", "unit": "关/日",
                 "range": "1", "calc": "按日期索引现有 20 关",
                 "rounding": "向下取整", "basis": "沿用现有 20 关,可复用"},
                {"name": "本机最佳记录条数", "value": "1", "unit": "条/日",
                 "range": "0-1", "calc": "每日只保留当日最佳",
                 "rounding": "不适用", "basis": "本机存档最小改动"},
            ],
            "trial": [
                {"name": "单局目标用步", "value": "40", "unit": "步",
                 "range": "30-60", "calc": "暂定目标", "rounding": "不适用",
                 "basis": "待原型试玩,试验值不作当前要求"},
            ],
            "sources": ["Q1"]},
        "feedback": {"content": "进入时显示当日日期与当前最佳;结算后显示本次"
                                "步数与最佳对比;未超过时提示保持原记录。",
                     "sources": ["Q1"]},
        "persistence": {"content": "保存每日种子与当日最佳步数;退出重进后当日"
                                   "最佳仍可读;跨日只读不回写。",
                        "sources": ["Q1"]},
        "acceptance": {
            "cases": [
                {"initial": "新档,当日未玩",
                 "action": "从主菜单进入每日挑战并完成一局",
                 "expected": "记录当日最佳步数,再次进入可读"},
                {"initial": "当日已有最佳 42 步", "action": "再玩一局 50 步",
                 "expected": "最佳仍是 42,并提示未超过"},
            ],
            "sources": ["Q1"]},
    }


def _handoff_meta(**over):
    meta = {
        "module": "每日挑战", "date": DATE,
        "record_path": RECORD_REL, "spec_path": SPEC_REL,
        "design_path": DESIGN_REL, "glossary_path": GLOSSARY_REL,
        "sync_ref": "GAME_DESIGN v3 / spec-每日挑战 v1",
        "version_from": "v2", "version_to": "v3", "change": "substantive",
        "authorization": {"write": True, "sync": True},
        "sections": _spec_sections(), "glossary": [], "adr": [],
        "scope_change": [], "verification": [], "proposals": [],
        "assumptions": [], "pending_impacts": {}, "blocking_qids": [],
        "untouched": [PROJECT_REL, TECH_REL],
    }
    meta.update(over)
    return meta


def _domains(*, ui_gap=True):
    domains = {
        "project": {"applies": True, "rules": PROJECT_REL,
                    "impact_level": "global"},
        "appeal": {"applies": True, "rules": f"{DESIGN_REL}（核心体验一节）"},
        "core_play": {"applies": True, "rules": SPEC_REL,
                      "impact_level": "global",
                      "proposals": [{"kind": "数值", "detail": "单局目标 40 步",
                                     "basis": "沿用现有 20 关平均步数",
                                     "serves": "核心玩法"}]},
        "journey": {"applies": True,
                    "rules": f"{DESIGN_REL}（完整游玩过程一节）"},
        "systems": {"applies": True, "rules": SPEC_REL},
        "growth": {"applies": True, "rules": f"{SPEC_REL}（数值与配置）",
                   "rework_risk": "high"},
        "content": {"applies": True, "rules": CONTENT_REL},
        "presentation": {"applies": True, "rules": CONTENT_REL},
        "release": {"applies": False,
                    "reason": "本作只做本地游玩,不上架商店,无商业化与发布需求"},
        "tech": {"applies": "unknown",
                 "method": "读取 TECH_DESIGN.md 核对存档格式与设备范围",
                 "impact": "决定存档兼容与设备范围"},
        "version": {"applies": True, "rules": VERSION_REL},
    }
    if ui_gap:
        domains["ui"] = {
            "applies": True,
            "gap": "每日挑战入口的页面流转与错误恢复未写清",
            "method": "下一轮讨论入口、返回与失败提示",
            "impact": "影响界面与引导制作",
            "blocks": True, "impact_level": "global"}
    else:
        domains["ui"] = {"applies": True,
                         "rules": f"{DESIGN_REL}（操作、界面与引导一节）"}
    return domains


def _journey():
    return {
        "first_entry": {"status": "closed", "detail": "从主菜单进入每日挑战"},
        "understand_goal": {"status": "closed",
                            "detail": "入口显示当日日期与当前最佳"},
        "operate": {"status": "closed", "detail": "推箱操作与章节一致"},
        "choose": {"status": "closed", "detail": "每步可选择推动方向"},
        "result": {"status": "closed", "detail": "结算显示本次步数与最佳对比"},
        "end": {"status": "closed", "detail": "完成或主动退出均可回主菜单"},
        "reenter": {"status": "closed", "detail": "再次进入读取当日最佳"},
    }


def _checks():
    return {
        "resource_exhaustion": {"applies": True,
                                "detail": "步数无上限,不消耗可耗尽资源"},
        "repeat": {"applies": True,
                   "detail": "同日重复进行只有更优成绩覆盖最佳"},
        "exit": {"applies": True, "detail": "中途退出不记录最佳"},
        "unlock": {"applies": True,
                   "detail": "每日挑战需齿轮币解锁,金额见经济条目"},
        "failure_recovery": {"applies": False, "reason": "无失败状态,关卡可重试"},
    }


def _economy(unlock_amount):
    return {
        "resources": [{"name": "齿轮币", "unit": "枚", "earn_total": 20,
                       "earn_sources": ["主线 20 关每关 1 枚"],
                       "spend_total": 20,
                       "spend_sinks": ["解锁每日挑战"]}],
        "unlock_requirements": [{"target": "每日挑战", "resource": "齿轮币",
                                 "amount": unlock_amount,
                                 "location": SPEC_REL}],
    }


def _material(*, ui_gap=True, unlock_amount=30, vision_leak=False,
              module_status="handoffable", module_gaps=None, focus_limit=3,
              clarify=None):
    current_required = ["十二领域覆盖无阻断缺口", "关键流程闭合",
                        "必要模块规格可交接"]
    met_current = (["关键流程闭合", "必要模块规格可交接"] if ui_gap
                   else list(current_required))
    current = [{"text": "每日挑战本机模式", "source": "decision"},
               {"text": "沿用现有 20 关按日期抽取", "source": "decision"}]
    if vision_leak:
        current.append({"text": "联机对战模式", "source": "vision"})
    return {
        "known": {
            "gameplay": ["推箱开门,齿轮接通传动链"],
            "visuals": ["齿轮与金属管道风格"],
            "operations": ["方向键推箱,一步一格"],
            "feelings": ["短局解谜,失败可重来"],
            "references": ["参考经典推箱子,增加齿轮连锁"],
        },
        "experience": [
            {"text": "进入关卡,推齿轮块接通传动链开门",
             "source": "intent"},
            {"text": "每日挑战复用现有 20 关", "source": "intent"},
            {"text": "结算时给出步数评价", "source": "proposal"},
            {"text": "结束演出未定", "source": "gap"},
        ],
        "scope": {
            "vision": ["联机对战模式", "每日排行榜"],
            "current": current,
            "later": ["每日排行榜(需要联网能力,先列入后续方向)"],
            "out_of_scope": ["付费商店与内购"],
            "clarify": list(clarify or []),
        },
        "domains": _domains(ui_gap=ui_gap),
        "journey": _journey(),
        "checks": _checks(),
        "economy": _economy(unlock_amount),
        "design": {
            "overview": "章节式推箱解谜,新增每日挑战本机模式。",
            "core_experience": "短局解谜与每日回来的理由。",
            "core_loop": "进入关卡 → 推箱接通传动链 → 开门过关 → 结算。",
            "system_relations": "每日挑战引用章节关卡与种子规则;不修改章节进度。",
        },
        "content": {
            "levels_events": [{"text": "每日一关,从现有 20 关按日期抽取",
                               "rules": ["daily-seed"]}],
            "templates": [{"text": "直接复用章节关卡模板", "rules": []}],
            "characters": [{"text": "无新角色,沿用推箱小人", "rules": []}],
            "scenes": [{"text": "沿用齿轮与管道场景", "rules": []}],
            "ui": [{"text": "主菜单增加每日挑战入口", "rules": []}],
            "animation_vfx": [{"text": "传动链接通的既有表现", "rules": []}],
            "audio": [{"text": "沿用现有音效", "rules": ["daily-seed"]}],
        },
        "rules": [{"id": "daily-seed", "title": "每日种子规则",
                   "location": SPEC_REL, "text": "本机日历日加固定种子"}],
        "prototype": [
            {"question": "每日一局是否有重复游玩的动力",
             "goal": "确认每日挑战的长期吸引力",
             "method": "原型内连续 3 天试玩并记录每日完成率",
             "judgement": "3 天完成率不低于 60%",
             "blocks_stage": False},
        ],
        "acceptance": [
            {"initial": "新档,当日未玩",
             "action": "从主菜单进入每日挑战并完成一局",
             "expected": "记录当日最佳步数,再次进入可读"},
        ],
        "risks": ["联网排行榜当前无联网能力,列入后续方向"],
        "dependencies": ["沿用现有 20 关内容与既有存档"],
        "existing": {
            "materials": [{"path": PROJECT_REL}, {"path": SPEC_REL},
                          {"path": RECORD_REL}],
            "decisions": [{"qid": "Q1", "value": "A 从现有 20 关按日期抽取"}],
        },
        "stage_evidence": {
            "concept": {"required": ["核心吸引力明确", "范围边界明确"],
                        "met": ["核心吸引力明确", "范围边界明确"]},
            "prototype_spec": {"required": ["核心规则可执行", "原型验证问题有方法"],
                               "met": ["核心规则可执行", "原型验证问题有方法"]},
            "current_version": {"required": list(current_required),
                                "met": met_current},
        },
        "focus_limit": focus_limit,
        "_module_status": module_status,
        "_module_gaps": list(module_gaps or []),
    }


def _full_meta(material=None, **over):
    status = (material or {}).get("_module_status") or "handoffable"
    gaps = list((material or {}).get("_module_gaps") or [])
    meta = {
        "game": "齿轮谜城", "date": DATE,
        "version_from": "v3", "version_to": "v4",
        "doc_map": {"design": DESIGN_REL, "content": CONTENT_REL,
                    "version": VERSION_REL,
                    "records": "docs/mygamestudio/records/",
                    "project": PROJECT_REL, "tech": TECH_REL},
        "module_specs": [{"module": "每日挑战", "spec_path": SPEC_REL,
                          "status": status, "gaps": gaps}],
        "necessary_modules": ["每日挑战"],
        "records": [RECORD_REL],
        "authorization": {"write": True, "sync": True, "product": False},
        "untouched": [PROJECT_REL, TECH_REL],
    }
    meta.update(over)
    return meta


def _existing(project: Path):
    def read(path):
        target = project / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    return {path: read(path) for path in (
        DESIGN_REL, CONTENT_REL, VERSION_REL, PROJECT_REL, TECH_REL,
        SPEC_REL, RECORD_REL, GLOSSARY_REL, PENDING_REL, EXIT_SPEC_REL)}


def _stub_existing():
    """不依赖临时项目的既有内容:适用于只核对缺口判定的场景。"""

    return {
        DESIGN_REL: "# 齿轮谜城:当前游戏需求与设计\n\n基线版本:v3。\n",
        CONTENT_REL: _original_content(), VERSION_REL: None,
        SPEC_REL: "# 每日挑战:模块规格\n\n## 设计目的\n\n有具体规则。\n",
        RECORD_REL: None, PROJECT_REL: "# 项目目标\n",
        TECH_REL: "# 技术设计\n",
    }


def _blocked_material():
    """固定场景的初始成稿材料:界面领域缺口 + 模块规格未完成 + 植入矛盾。"""

    material = _material()
    material["_module_status"] = "draft"
    material["_module_gaps"] = ["每日挑战入口流程未写清"]
    return material


def _resolved(material):
    """处理真实影响后的材料:覆盖闭合、模块可交接、资源与解锁一致。"""

    fixed = dict(material)
    fixed["domains"] = {**_domains(ui_gap=False),
                        "tech": {"applies": True, "rules": TECH_REL}}
    fixed["economy"] = _economy(20)
    fixed["_module_status"] = "handoffable"
    fixed["_module_gaps"] = []
    return fixed


def test_extracts_known_material_and_builds_coverage_map() -> None:
    """想法片段与已有资料:整理典型游玩经历,建立十二领域覆盖地图。"""

    material = _material(vision_leak=True)
    material["domains"]["growth"] = {
        "applies": True, "gap": "齿轮币收支与解锁关系尚未写成规则",
        "method": "下一轮给出数值", "impact": "影响成长与解锁", "blocks": True}
    material["domains"]["content"] = {
        "applies": True, "gap": "每日关内容复用范围未写清",
        "method": "列出复用关卡清单", "impact": "影响内容制作量",
        "rework_risk": "high"}
    result = build_map(material)
    check([key for key, _title in DOMAINS] == list(DOMAIN_KEYS),
          f"覆盖地图须按规格顺序覆盖十二领域,实际 {[k for k, _ in DOMAINS]}")
    titles = [title for _key, title in DOMAINS]
    for expected in ("项目目标与边界", "核心吸引力", "核心玩法与决策",
                     "完整游玩过程", "系统与相互关系", "成长与资源流动",
                     "内容与叙事", "操作、界面与引导", "美术、动画与声音",
                     "商业化与发布需求", "技术与数据约束", "版本范围与验收"):
        check(expected in titles, f"覆盖地图须包含领域 {expected}")
    check(set(result["domains"]) == set(DOMAIN_KEYS),
          "十二领域须逐项给出适用性、状态与规则或缺口定位")
    sources = {item["source"] for item in result["experience"]}
    check(sources == {"原始意图", "助手提案", "信息缺口"},
          f"典型游玩经历须标明原始意图、助手提案与信息缺口,实际 {sources}")
    texts = "".join(item["text"] for item in result["experience"])
    check("推箱开门" in texts and "每日挑战复用" in texts,
          "须从玩法片段、操作与感受提取已知内容,不要求用户重讲")
    reused = "".join(result["reused"])
    check("PROJECT.md" in reused and "Q1" in reused,
          f"已有有效资料与决定须沿用,实际 {result['reused']}")
    check(result["domains"]["project"]["status"] == "rule"
          and result["domains"]["release"]["status"] == "not_applicable"
          and result["domains"]["ui"]["status"] == "gap"
          and result["domains"]["tech"]["status"] == "unknown",
          f"领域状态须区分已有规则/不适用/缺口/未知,实际 "
          f"{ {k: v['status'] for k, v in result['domains'].items()} }")
    check(result["domains"]["release"]["reason"],
          "不适用领域须给出理由")
    check(result["domains"]["tech"]["status"] != "not_applicable",
          "未查清的领域不得冒充不适用")
    focus = result["next_focus"]
    check(len(focus) == 3 and focus[0]["domain"] == "ui",
          f"推进焦点须按阻断与影响排序且不一次抛全套问卷,实际 {focus}")
    check(all(item["why"] for item in focus),
          "每个推进焦点须说明为什么优先")
    proposals = result["proposals"]
    check(proposals and proposals[0]["kind"] == "数值"
          and proposals[0]["adopted"] is False,
          f"AI 提出的数值/规则/边界方案保持提案身份,实际 {proposals}")
    check(result["template_fill"] == [],
          "有依据且服务已有范围的提案不判为填充模板")
    check(all(item["domain"] != "release" for item in focus),
          "不适用领域不进推进焦点")


def test_scope_layers_and_template_fill_guard() -> None:
    """完整愿景/当前成稿/后续方向/范围外分开;不为填模板新增系统。"""

    material = _material(vision_leak=True)
    material["domains"]["release"] = {
        "applies": True, "rules": CONTENT_REL}
    material["domains"]["growth"] = {
        "applies": True, "proposals": []}
    material["scope"]["clarify"] = [{"question": "首发是否包含每日挑战",
                                     "why_needed": "决定当前版本范围与验收对象"}]
    result = build_map(material)
    check(result["scope"]["vision"] == ["联机对战模式", "每日排行榜"],
          "完整愿景须与当前版本分开保存")
    current_texts = [item["text"] for item in result["scope"]["current"]]
    check("每日挑战本机模式" in current_texts,
          f"当前成稿版本须来自已采纳决定,实际 {current_texts}")
    check("联机对战模式" not in current_texts,
          "后续愿景不得自动列入当前首发任务")
    check(all("联机对战" not in item["text"] for item in result["scope"]["current"]),
          "被标为愿景的内容不得混入当前版本")
    check(result["scope"]["later"]
          and "每日排行榜" in result["scope"]["later"][0],
          f"后续方向须单独保留,实际 {result['scope']['later']}")
    check("付费商店与内购" in result["scope"]["out_of_scope"],
          "范围外内容须明确列出")
    check(result["scope"]["clarify"] == [{"question": "首发是否包含每日挑战",
                                          "why_needed": "决定当前版本范围与验收对象"}],
          f"当前范围不足时只澄清必要取舍,实际 {result['scope']['clarify']}")
    check(result["template_fill"] == [],
          "有依据且服务已有范围的提案不得被当成填充模板")
    check(result["domains"]["release"]["status"] == "rule",
          "有规则的不适用改判须按实际给规则")

    empty = _material()
    empty["domains"]["release"] = {"applies": True}
    empty["domains"]["growth"] = {"applies": True,
                                  "proposals": [{"kind": "系统",
                                                 "detail": "增加每日任务系统"}]}
    empty["domains"]["version"] = {"applies": "unknown"}
    second = build_map(empty)
    check(any("每日任务系统" in item["detail"]
              for item in second["template_fill"]),
          f"无依据且为填满模板的新增系统须标出,实际 {second['template_fill']}")
    check(second["domains"]["release"]["status"] == "gap",
          "不适用但不给理由须判为缺口")
    check(second["domains"]["version"]["status"] == "unknown",
          "未查清不得冒充不适用")


def test_stage_boundaries_follow_required_outcomes_not_round_count() -> None:
    """阶段边界由所需成果决定:概念/原型规格/当前版本完整设计。"""

    material = _material()
    concept = stage_status(material, stage="concept")
    check(concept["stage"] == "concept" and concept["label"] == "概念说明"
          and concept["complete"] is True and concept["missing"] == [],
          f"概念说明由所需成果判定完成,实际 {concept}")
    proto = stage_status(material, stage="prototype_spec")
    check(proto["label"] == "原型所需规格" and proto["complete"] is True,
          f"原型规格按核心规则与验证方法判定,实际 {proto}")
    current = stage_status(material, stage="current_version")
    check(current["label"] == "当前版本完整设计"
          and current["complete"] is False
          and current["missing"],
          f"当前版本完整设计须按覆盖与交接成果判定,实际 {current}")

    blocked = dict(material)
    blocked["stage_evidence"] = {
        **material["stage_evidence"],
        "concept": {"required": ["核心吸引力明确", "范围边界明确"],
                    "met": ["核心吸引力明确"]},
    }
    check(stage_status(blocked, stage="concept")["complete"] is False,
          "缺所需成果时阶段不得判为完成")
    record = stage_status(material, stage="current_version",
                          rounds=3, pages=12)
    check(record["complete"] == current["complete"]
          and record["missing"] == current["missing"],
          "阶段完成不以轮数或页数判定,只按所需成果")
    thin = dict(material)
    thin["stage_evidence"] = {**material["stage_evidence"],
                              "concept": {"required": [], "met": []},
                              "prototype_spec": {"required": [], "met": []},
                              "current_version": {"required": [],
                                                  "met": []}}
    empty_stage = stage_status(thin, stage="concept")
    check(empty_stage["complete"] is False and empty_stage["missing"],
          "没有所需成果时不因目录齐全判为完成")


def test_journey_walkthrough_finds_existing_contradiction() -> None:
    """玩家视角全程核对:既有的资源/解锁矛盾必须被检出并指明关系。"""

    material = _material(unlock_amount=30)
    result = walkthrough(material)
    order = [step["id"] for step in result["steps"]]
    check(order == ["first_entry", "understand_goal", "operate", "choose",
                    "result", "end", "reenter"],
          f"须覆盖首次进入、理解目标、操作、选择、结果、结束与再次进入,实际 {order}")
    checks = result["checks"]
    check(set(checks) == {"resource_exhaustion", "repeat", "exit", "unlock",
                          "failure_recovery"},
          f"须检查适用的资源耗尽、重复操作、退出、解锁与失败恢复,实际 {set(checks)}")
    check(checks["failure_recovery"]["status"] == "n/a"
          and checks["failure_recovery"]["reason"],
          "不适用须给出理由,不逐个规则强判")
    contradictions = find_contradictions(material)
    kinds = {item["kind"] for item in contradictions}
    check("资源或解锁矛盾" in kinds,
          f"资源收支与解锁要求矛盾须被发现,实际 {contradictions}")
    item = next(item for item in contradictions
                if item["kind"] == "资源或解锁矛盾")
    check("齿轮币" in item["detail"] and "30" in item["detail"],
          f"矛盾须指明资源、总量与解锁要求的实际数值,实际 {item['detail']}")
    check(item["impact"] and item["affects"],
          f"每处矛盾须给出影响范围,实际 {item}")
    check(result["contradictions"] == contradictions,
          "walkthrough 须汇总同一矛盾判定")
    missing = find_contradictions(_material(unlock_amount=20))
    check(missing == [], f"无矛盾时不得误报,实际 {missing}")


def _run_full_flow(root: Path, *, material=None):
    """固定小型游戏场景的完整流程:问答 → 保存 → 模块规格交接 → 成稿交付。"""

    svc, project = _service(root)
    save_owner = _instance(svc)
    save_channel = _Channel(svc, save_owner.token)
    read = _reader(project)
    material = material or _material()
    settled = _save_decisions(save_channel, read, (
        ("Q1 选 A, Q2 选 B", ["Q1", "Q2", "Q3"]),
        ("Q3 选 A", ["Q3"]),
    ))
    spec_plan = plan_handoff({RECORD_REL: read(RECORD_REL)},
                             _handoff_meta(), _existing(project))
    check(spec_plan["status"] == "planned",
          f"模块规格应可交接,实际 {spec_plan.get('status')}:{spec_plan.get('gaps')}")
    save_channel.svc.release_instance(save_owner.instance_id)
    save_channel.svc.reclaim_locks(save_owner.instance_id)
    spec_owner = _instance(svc, purpose="spec_sync",
                           resources=["docs/mygamestudio/records/**",
                                      DESIGN_REL])
    spec_channel = _Channel(svc, spec_owner.token)
    applied = apply_handoff(spec_plan, spec_channel, read)
    check(applied["saved"] is True,
          f"模块规格须经真实接缝落盘,实际 {applied.get('status')}")
    spec_channel.svc.release_instance(spec_owner.instance_id)
    spec_channel.svc.reclaim_locks(spec_owner.instance_id)
    return svc, project, read, material, applied


def test_full_flow_delivers_four_outputs_and_detects_planted_contradiction() -> None:
    """完整流程:四类交付物齐备,植入的资源/解锁矛盾被发现,不误报完成。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project, read, material, applied = _run_full_flow(
            Path(tmp), material=_blocked_material())
        channel = _Channel(svc, _handoff_token(svc))
        plan = plan_delivery(_existing(project), _full_meta(material),
                             material)
        check(plan["status"] == "incomplete",
              f"有阻断缺口或矛盾时不得宣布完成,实际 {plan['status']}")
        kinds = {item["kind"] for item in plan["contradictions"]}
        check("资源或解锁矛盾" in kinds,
              f"植入的资源/解锁矛盾须被发现,实际 {plan['contradictions']}")
        check(plan["contradictions"][0]["kind"] == "资源或解锁矛盾"
              and "齿轮币" in plan["report"],
              f"报告须引用实际记录指出矛盾,实际 {plan['report']}")
        needled = {item["needle"] for item in plan["missing"]}
        check({"覆盖:操作、界面与引导", "模块:每日挑战"} <= needled,
              f"须分别报出领域覆盖缺口与模块缺口,实际 {plan['missing']}")
        applied_bad = apply_delivery(plan, channel, read)
        check(applied_bad["saved"] is False and applied_bad["written"] == [],
              f"未达交接标准不得写入交付物,实际 {applied_bad['written']}")
        check(read(CONTENT_REL) == _original_content()
              and read(VERSION_REL) is None,
              "未完成交付不得改动既有资料或新建交付物")

        fixed = _resolved(material)
        good = plan_delivery(_existing(project), _full_meta(fixed), fixed)
        check(good["status"] == "planned",
              f"缺口消除且矛盾处理后应可交付,实际 {good['status']}:{good['missing']}")
        check(good["contradictions"] == [] and good["handoff_ready"] is True,
              f"无矛盾且覆盖闭合时才可交接,实际 {good}")
        applied_good = apply_delivery(good, channel, read)
        check(applied_good["status"] == "saved",
              f"应经受控通道落盘,实际 {applied_good.get('status')}")
        four = {item["path"]: item["role"] for item in applied_good["outputs"]}
        check(set(four) == {DESIGN_REL, SPEC_REL, CONTENT_REL, VERSION_REL},
              f"四类交付物须齐备,实际 {four}")
        check(TEST_ANSWER in read(RECORD_REL),
              "验收依据须留明确标注的测试回答,不冒充真实开发者决定")
        check(four[DESIGN_REL] == "游戏设计主文档"
              and four[SPEC_REL] == "系统规则与数值"
              and four[CONTENT_REL] == "内容与视听制作需求"
              and four[VERSION_REL] == "版本与验证方案",
              f"四类交付角色须明确,实际 {four}")
        check(good["entry"] == DESIGN_REL and DESIGN_REL in good["report"],
              f"须提供清晰入口,实际 {good['entry']}")
        check(SPEC_REL in plan["report"] or SPEC_REL in good["report"],
              "主文档与系统规则须可相互定位")
        check(read(CONTENT_REL) != _original_content()
              and "沿用现有音效" in read(CONTENT_REL),
              "内容与视听需求须保留既有说明并追加本轮需求")
        version = read(VERSION_REL)
        check(all(x in version for x in ("概念说明", "原型所需规格",
                                         "当前版本完整设计")),
              f"版本交付须含阶段与范围,实际 {version}")
        check("每日一局是否有重复游玩的动力" in version
              and "3 天完成率不低于 60%" in version
              and "是否阻断当前阶段：否" in version,
              "原型与试玩事项须含目标、方法与判定依据及是否阻断")
        check("未验证" in applied_good["report"]
              and "未实现" in applied_good["report"],
              f"无实际证据不得报告体验或市场效果已验证,实际 {applied_good['report']}")
        check(applied_good["states"]["verified"] is False
              and applied_good["states"]["implemented"] is False,
              "实现与验证状态不得混入交付完成")
        check(CONTENT_REL in applied_good["report"]
              and VERSION_REL in applied_good["report"]
              and DESIGN_REL in applied_good["report"],
              f"报告须如实列出实际交付范围,实际 {applied_good['report']}")
        verdict = verify_delivery(good, {
            DESIGN_REL: read(DESIGN_REL), SPEC_REL: read(SPEC_REL),
            CONTENT_REL: read(CONTENT_REL), VERSION_REL: read(VERSION_REL),
            RECORD_REL: read(RECORD_REL), PROJECT_REL: read(PROJECT_REL),
            TECH_REL: read(TECH_REL)})
        check(verdict["ok"], f"回读核对应通过,实际 {verdict}")
        check(read(PROJECT_REL).startswith("# 项目目标")
              and read(TECH_REL).startswith("# 技术设计"),
              "管理资料与技术设计不得被代写")


def _mutate(material, **changes):
    result = dict(material)
    result.update(changes)
    return result


def _with_domain(material, key, **changes):
    result = dict(material)
    domains = {name: dict(item)
               for name, item in material["domains"].items()}
    domains[key] = {**domains.get(key, {}), **changes}
    result["domains"] = domains
    return result


def test_delivery_detects_each_blocking_gap_without_false_completion() -> None:
    """交接标准的每类阻断缺口分别检出:覆盖、流程、模块、范围、规则、未知。"""

    material = _resolved(_material())
    base_meta = _full_meta(material)
    cases = {
        "覆盖:操作、界面与引导": (
            _with_domain(material, "ui",
                         gap="入口页面流转未写清", method="下一轮澄清",
                         impact="影响界面制作", blocks=True),
            base_meta),
        "流程:结束": (
            _mutate(material, journey={**_journey(),
                                       "end": {"status": "open",
                                               "detail": "结束演出未定"}}),
            base_meta),
        "模块:每日挑战": (
            _mutate(material, _module_status="draft",
                    _module_gaps=["每日挑战入口流程未写清"]),
            {**base_meta, "module_specs": [
                {"module": "每日挑战", "spec_path": SPEC_REL,
                 "status": "draft", "gaps": ["每日挑战入口流程未写清"]}]}),
        "范围:首发是否包含每日挑战": (
            _mutate(material, scope={**_material()["scope"],
                                     "clarify": [{"question":
                                                  "首发是否包含每日挑战",
                                                  "why_needed":
                                                  "决定当前版本范围"}]}),
            base_meta),
        "规则:daily-seed": (
            _mutate(material, rules=[{"id": "daily-seed",
                                      "title": "每日种子规则",
                                      "location": SPEC_REL,
                                      "text": "规则合理、强度适中即可"}]),
            base_meta),
        "规则一致:daily-seed": (
            _mutate(material, rules=[{"id": "other-rule",
                                      "title": "别处规则",
                                      "location": SPEC_REL,
                                      "text": "本机日历日加固定种子"}]),
            base_meta),
        "未知:技术与数据约束": (
            _mutate(material, domains={**material["domains"],
                                       "tech": {"applies": "unknown"}}),
            base_meta),
        "阻断:Q4": (
            material,
            {**base_meta, "blocking_qids": ["Q4"]}),
    }
    for needle, (mutated, meta) in cases.items():
        plan = plan_delivery(_stub_existing(), meta, mutated)
        check(plan["status"] == "incomplete",
              f"缺口 {needle} 未阻断时不得宣布完成,实际 {plan['status']}")
        needled = {item["needle"] for item in plan["missing"]}
        check(needle in needled,
              f"须报出 {needle},实际 {sorted(needled)}")
        check(not any(each.startswith("模块:") for each in needled)
              or needle.startswith("模块:")
              or meta.get("module_specs") == base_meta.get("module_specs"),
              "未涉及的模块不得被顺带报缺")
    clean = plan_delivery(_stub_existing(), base_meta, material)
    check(clean["status"] == "planned" and clean["missing"] == [],
          f"全部闭合时不得误报缺口,实际 {clean.get('missing')}")


def test_delivery_writes_only_with_authorization_and_keeps_existing_docs() -> None:
    """交付写入遵守授权边界:只读不写入,缺同步授权保留待办,不代写管理资料。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project, read, material, applied = _run_full_flow(
            Path(tmp), material=_blocked_material())
        fixed = _resolved(material)
        meta = _full_meta(fixed)
        read_only = plan_delivery(_existing(project),
                                  {**meta, "authorization": {"write": False}},
                                  fixed)
        check(read_only["status"] == "read_only"
              and read_only["saved"] is False,
              f"无写入授权时只读,实际 {read_only['status']}")
        blocked = apply_delivery(read_only, _Channel(svc, _handoff_token(svc)),
                                 read)
        check(blocked["saved"] is False and blocked["written"] == [],
              f"只读不得写入,实际 {blocked['written']}")
        check("未保存" in blocked["report"] and "未同步" in blocked["report"],
              f"只读报告须如实说明,实际 {blocked['report']}")
        check(read(VERSION_REL) is None and read(CONTENT_REL) == _original_content(),
              "只读不得留下交付物或改动既有资料")

        unsynced = plan_delivery(_existing(project),
                                 {**meta, "authorization": {"write": True,
                                                            "sync": False}},
                                 fixed)
        check(unsynced["status"] == "planned"
              and unsynced["sync_authorized"] is False,
              f"缺同步授权仍可整理交付,实际 {unsynced['status']}")
        before_design = read(DESIGN_REL)
        before_content = read(CONTENT_REL)
        result = apply_delivery(unsynced,
                                _Channel(svc, _handoff_token(svc)), read)
        check(result.get("states", {}).get("synced") is not True,
              f"缺同步授权不得宣称已同步,实际 {result.get('states')}")
        check(result.get("handoff_ready") is not True,
              "缺同步授权不得宣称完整设计可交接")
        check(result.get("to_sync"),
              f"须留下可定位的待同步项,实际 {result.get('to_sync')}")
        check(DESIGN_REL not in {item["path"] for item in unsynced["files"]},
              f"缺同步授权不得把当前有效主文档列入写入计划,实际 {unsynced['files']}")
        pending_path = "docs/mygamestudio/records/delivery-pending.md"
        check(pending_path in {item["path"] for item in unsynced["files"]},
              f"缺同步授权须留下待同步记录,实际 {unsynced['files']}")
        check(read(DESIGN_REL) == before_design,
              "缺同步授权不得改写 GAME_DESIGN")
        check(read(pending_path) and "缺同步授权" in read(pending_path),
              "待同步记录须可回读")
        check(read(CONTENT_REL) == before_content,
              "缺同步授权不得改写现行内容需求")
        check(read(VERSION_REL) is None,
              "缺同步授权不得新建当前有效版本方案")
        roles = {item["path"]: item["role"] for item in result["outputs"]}
        check(set(roles) == {DESIGN_REL, SPEC_REL, CONTENT_REL, VERSION_REL}
              and roles[VERSION_REL] == "版本与验证方案"
              and roles[DESIGN_REL] == "游戏设计主文档",
              f"交付角色须与文件一一对应,实际 {roles}")
        check("未实现" in result["report"] and "未验证" in result["report"],
              "状态分档须保留")

        before_project = read(PROJECT_REL)
        before_tech = read(TECH_REL)
        check(read(PROJECT_REL) == before_project
              and read(TECH_REL) == before_tech,
              "管理资料与技术设计不得被代写")
        check(PROJECT_REL in result["untouched"]
              and TECH_REL in result["untouched"],
              f"不受影响范围须声明,实际 {result['untouched']}")


def _original_content() -> str:
    return ("# 齿轮谜城:内容与视听制作需求\n\n"
            "既有说明：音效全部沿用现有素材,不新增录音。\n")


def test_cli_smoke_full_design_entry() -> None:
    """CLI 冒烟:check 只读与 apply 经真实受控通道,失败场景非零退出。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project, read, material, applied = _run_full_flow(
            root, material=_blocked_material())
        token = _handoff_token(svc)
        cli = str(SKILL_DIR / "full_design_cli.py")
        meta = _full_meta(material)

        def run_cli(action, payload, *args, token=token):
            return subprocess.run(
                [sys.executable, "-B", cli, action, "--project-root",
                 str(project), "--runtime-root", str(root / "runtime"),
                 "--token", token, *args],
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True, text=True)

        blocked = run_cli("check", {"meta": meta, "material": material})
        check(blocked.returncode == 0, f"check 应可运行,实际 {blocked.stderr}")
        blocked_result = json.loads(blocked.stdout)
        check(blocked_result["status"] == "incomplete"
              and blocked_result["handoff_ready"] is False,
              f"有缺口与矛盾时须报未完成,实际 {blocked_result['status']}")
        check(read(VERSION_REL) is None, "check 不得写入")

        payload = {"meta": meta, "material": material}
        failed = run_cli("apply", payload)
        check(failed.returncode == 1,
              f"未达交接标准的 apply 须非零退出,实际 {failed.returncode}")
        check(json.loads(failed.stdout)["saved"] is False,
              "未完成不得报告已保存")
        check(read(VERSION_REL) is None, "未完成不得写入交付物")

        fixed = _resolved(material)
        saved = run_cli("apply", {"meta": _full_meta(fixed), "material": fixed})
        check(saved.returncode == 0, f"完整交付应成功,实际 {saved.stderr}")
        applied_result = json.loads(saved.stdout)
        check(applied_result["status"] == "saved"
              and applied_result["saved"] is True,
              f"须经真实受控通道落盘,实际 {applied_result}")
        check(set(item["path"] for item in applied_result["outputs"])
              == {DESIGN_REL, SPEC_REL, CONTENT_REL, VERSION_REL},
              f"CLI 冒烟须留四类交付物作证,实际 {applied_result['outputs']}")
        check("## 版本与验证方案" in read(VERSION_REL)
              or "每日一局是否有重复游玩的动力" in read(VERSION_REL),
              "版本与验证方案须含原型验证事项")
        check(read(PROJECT_REL).startswith("# 项目目标"),
              "不得代写 PROJECT")

        verified = run_cli("verify", {"meta": _full_meta(fixed),
                                      "material": fixed})
        check(verified.returncode == 0, f"verify 应成功,实际 {verified.stderr}")
        check(json.loads(verified.stdout)["ok"] is True,
              f"verify 须回读核对四类交付,实际 {verified.stdout}")

        unsupported = run_cli(
            "apply", {"meta": {**_full_meta(fixed),
                               "authorization": {"write": False}},
                      "material": fixed})
        check(unsupported.returncode == 1
              and json.loads(unsupported.stdout)["status"] == "read_only",
              f"未授权须报告只读,实际 {unsupported.stdout}")


def test_skill_entry_documents_full_design_flow() -> None:
    """Game-Design 入口须说明成稿流程与接缝。"""

    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("coverage_map.py", "journey.py", "full_design.py",
                   "full_design_cli.py", "十二", "覆盖地图", "完整愿景",
                   "当前成稿版本", "后续方向", "范围外", "四类交付",
                   "游戏设计主文档", "内容与视听制作需求", "版本与验证方案",
                   "交接", "不适用", "待验证", "不自动启动制作"):
        check(needle in text, f"Game-Design 入口须说明 {needle}")


def test_missing_delivery_locations_keep_draft() -> None:
    """四类交付缺权威位置时保持草案,不得过滤后宣称可交接。"""

    material = _resolved(_material())
    meta = _full_meta(material)
    meta["doc_map"] = {"design": DESIGN_REL, "content": "", "version": "",
                       "records": "docs/mygamestudio/records/",
                       "project": PROJECT_REL, "tech": TECH_REL}
    meta["module_specs"] = [{"module": "每日挑战", "spec_path": "",
                             "status": "handoffable", "gaps": []}]
    plan = plan_delivery(_stub_existing(), meta, material)
    check(plan["status"] == "incomplete",
          f"缺少交付位置须保持草案,实际 {plan['status']}")
    check(plan.get("handoff_ready") is not True,
          "残缺交付不得标可交接")
    needles = {item["needle"] for item in plan["missing"]}
    check(any(item.startswith("位置:") for item in needles),
          f"须报出缺失的交付位置,实际 {sorted(needles)}")
    applied = apply_delivery(plan, object(), lambda path: None)
    check(applied["saved"] is not True and applied.get("written") in (None, []),
          f"残缺交付不得写入,实际 {applied}")
    verdict = verify_delivery(plan, {DESIGN_REL: _stub_existing()[DESIGN_REL]})
    check(verdict["ok"] is False,
          f"缺三类位置时回读不得通过,实际 {verdict}")


def test_after_write_check_failure_does_not_complete_delivery() -> None:
    """保存后检查失败不得宣布完整设计已交付。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project, read, material, _applied = _run_full_flow(
            Path(tmp), material=_blocked_material())
        fixed = _resolved(material)
        content = dict(fixed.get("content") or {})
        content["audio"] = [{
            "text": "新增配乐依据见 docs/missing-audio-source.md",
            "rules": ["daily-seed"]}]
        fixed["content"] = content
        meta = _full_meta(fixed)
        plan = plan_delivery(_existing(project), meta, fixed)
        check(plan["status"] == "planned",
              f"引用缺口在写入后检查,计划仍可整理,实际 {plan.get('status')}")
        session = begin({
            "mode": "new_design", "stage": "只有设计，尚未实现",
            "goal": "完成每日挑战完整设计", "module": "每日挑战",
            "deps": [], "entry": DESIGN_REL,
            "authorization": {"write": True, "sync": True},
            "baseline": {DESIGN_REL: sha256_text(read(DESIGN_REL))},
        })["session"]
        applied = apply_delivery(plan, _Channel(svc, _handoff_token(svc)),
                                 read, session=session)
        check(applied.get("written"),
              f"已写入事实须保留,实际 {applied.get('written')}")
        check(applied["saved"] is not True
              and applied["status"] == "check_failed",
              f"检查失败不得标已保存或交付完成,实际 {applied}")
        check(applied.get("handoff_ready") is not True
              and applied.get("states", {}).get("synced") is not True,
              f"检查失败不得宣称已同步或可交接,实际 {applied}")
        check(applied.get("checks") and applied["checks"]["ok"] is False,
              f"须暴露 checks.ok=false,实际 {applied.get('checks')}")
        failures = "；".join(applied["checks"].get("failures") or [])
        check("docs/missing-audio-source.md" in failures,
              f"失败原因须可定位,实际 {failures}")
        check("已交付" not in applied["report"]
              or "检查失败" in applied["report"]
              or "未完成" in applied["report"],
              f"报告不得把检查失败写成已交付,实际 {applied['report']}")
        verdict = verify_delivery(plan, {
            DESIGN_REL: read(DESIGN_REL), SPEC_REL: read(SPEC_REL),
            CONTENT_REL: read(CONTENT_REL), VERSION_REL: read(VERSION_REL)})
        check(verdict["ok"] is False,
              f"检查失败后回读不得判交付完成,实际 {verdict}")


def test_missing_spec_file_keeps_delivery_incomplete() -> None:
    """权威模块规格路径有值但文件不存在时,不得宣布完整设计完成。"""

    material = _resolved(_material())
    meta = _full_meta(material)
    existing = {**_stub_existing(), SPEC_REL: None}
    plan = plan_delivery(existing, meta, material)
    check(plan["status"] == "incomplete",
          f"规格文件不存在须保持草案,实际 {plan['status']}")
    check(plan.get("handoff_ready") is not True,
          "缺少权威规格不得标可交接")
    needles = {item["needle"] for item in plan["missing"]}
    check(any("规格" in item or "系统规则" in item or SPEC_REL in item
              for item in needles),
          f"须报出缺失的权威规格,实际 {sorted(needles)}")
    applied = apply_delivery(plan, object(), lambda path: None)
    check(applied["saved"] is not True and applied.get("written") in (None, []),
          f"缺权威规格不得写入,实际 {applied}")
    verdict = verify_delivery(plan, {
        DESIGN_REL: existing[DESIGN_REL], SPEC_REL: None,
        CONTENT_REL: existing[CONTENT_REL], VERSION_REL: None})
    check(verdict["ok"] is False,
          f"缺权威规格时回读不得通过,实际 {verdict}")


def test_delivery_keeps_official_baseline_version_field() -> None:
    """完整成稿须保留正式接口能识别的基线版本字段。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project, read, material, _applied = _run_full_flow(
            Path(tmp), material=_blocked_material())
        fixed = _resolved(material)
        plan = plan_delivery(_existing(project), _full_meta(fixed), fixed)
        applied = apply_delivery(plan, _Channel(svc, _handoff_token(svc)), read)
        check(applied.get("saved") is True,
              f"完整成稿应落盘,实际 {applied}")
        design = read(DESIGN_REL) or ""
        check("基线版本" in design,
              f"主文档须保留基线版本字段,实际 {design}")
        records_dir = PLUGIN_ROOT / "records"
        if str(records_dir) not in sys.path:
            sys.path.insert(0, str(records_dir))
        import mgs_records  # noqa: PLC0415
        entry = next(item for item in mgs_records.baseline_report(project)["docs"]
                     if item["path"] == DESIGN_REL)
        check(entry.get("declared_version") == "v4",
              f"正式接口须读到基线版本 v4,实际 {entry}")


def test_delivery_verify_failure_sets_checks_ok_false() -> None:
    """完整交付核验失败时,结构化 checks 不得仍显示通过。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project, read, material, _applied = _run_full_flow(
            Path(tmp), material=_blocked_material())
        fixed = _resolved(material)
        plan = plan_delivery(_existing(project), _full_meta(fixed), fixed)
        check(plan["status"] == "planned",
              f"规划时应可整理,实际 {plan.get('status')}")
        (project / SPEC_REL).unlink()
        session = begin({
            "mode": "new_design", "stage": "只有设计，尚未实现",
            "goal": "完成每日挑战完整设计", "module": "每日挑战",
            "deps": [], "entry": DESIGN_REL,
            "authorization": {"write": True, "sync": True},
            "baseline": {DESIGN_REL: sha256_text(read(DESIGN_REL))},
        })["session"]
        applied = apply_delivery(plan, _Channel(svc, _handoff_token(svc)),
                                 read, session=session)
        check(applied.get("saved") is not True
              and applied.get("status") == "check_failed",
              f"规格被移除后不得标已保存,实际 {applied}")
        check(applied.get("checks") and applied["checks"].get("ok") is False,
              f"结构化 checks 须为失败,实际 {applied.get('checks')}")
        failures = "；".join(applied["checks"].get("failures") or [])
        check(SPEC_REL in failures or "不存在" in failures,
              f"失败原因须可定位缺失规格,实际 {failures}")


def test_second_required_module_spec_missing_keeps_delivery_incomplete() -> None:
    """第二个必要模块的规格缺失时,不得宣布完整交付。"""

    material = _resolved(_material())
    meta = _full_meta(material)
    meta["module_specs"] = [
        {"module": "每日挑战", "spec_path": SPEC_REL,
         "status": "handoffable", "gaps": []},
        {"module": "退出重进", "spec_path": EXIT_SPEC_REL,
         "status": "handoffable", "gaps": []},
    ]
    existing = {**_stub_existing(), EXIT_SPEC_REL: None}
    plan = plan_delivery(existing, meta, material)
    check(plan["status"] == "incomplete",
          f"第二份规格缺失须保持草案,实际 {plan['status']}")
    check(plan.get("handoff_ready") is not True,
          "缺少第二份权威规格不得标可交接")
    applied = apply_delivery(plan, object(), lambda path: None)
    check(applied["saved"] is not True
          and applied.get("written") in (None, []),
          f"缺第二份规格不得写入,实际 {applied}")
    verdict = verify_delivery(plan, {**existing, EXIT_SPEC_REL: None})
    check(verdict["ok"] is False,
          f"缺第二份规格时回读不得通过,实际 {verdict}")
    both = {**_stub_existing(), EXIT_SPEC_REL: "# 退出重进:模块规格\n"}
    ready = plan_delivery(both, meta, material)
    check(ready["status"] == "planned",
          f"两份规格都在时应可规划,实际 {ready.get('status')}:{ready.get('missing')}")
    paths = {item["path"] for item in ready["outputs"]}
    check(SPEC_REL in paths and EXIT_SPEC_REL in paths,
          f"交付入口须列出全部必要模块规格,实际 {ready['outputs']}")
    blank = _full_meta(material)
    blank["module_specs"] = [
        {"module": "每日挑战", "spec_path": SPEC_REL,
         "status": "handoffable", "gaps": []},
        {"module": "退出重进", "spec_path": "",
         "status": "handoffable", "gaps": []},
    ]
    missing_path = plan_delivery(_stub_existing(), blank, material)
    check(missing_path["status"] == "incomplete",
          f"第二模块缺少规格路径须保持草案,实际 {missing_path['status']}")


def test_cli_pending_sync_record_continues_and_updates() -> None:
    """待同步记录须纳入读取与续写,完成同步后状态也要更新。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project, read, material, _applied = _run_full_flow(
            root, material=_blocked_material())
        token = _handoff_token(svc)
        cli = str(SKILL_DIR / "full_design_cli.py")
        fixed = _resolved(material)

        def run_cli(payload):
            return subprocess.run(
                [sys.executable, "-B", cli, "apply", "--project-root",
                 str(project), "--runtime-root", str(root / "runtime"),
                 "--token", token],
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True, text=True)

        no_sync = {"meta": {**_full_meta(fixed),
                            "authorization": {"write": True, "sync": False}},
                   "material": fixed}
        first = run_cli(no_sync)
        first_result = json.loads(first.stdout)
        check(first.returncode == 0 and first_result.get("saved") is True,
              f"缺同步授权仍应留下待同步记录,实际 {first.stdout}{first.stderr}")
        check(read(PENDING_REL) and "缺同步授权" in read(PENDING_REL),
              "首次须写入待同步记录")

        second = run_cli(no_sync)
        second_result = json.loads(second.stdout)
        check(second_result.get("status") != "conflict",
              f"已有待同步记录须续写,不得误报版本冲突,实际 {second.stdout}")

        synced = run_cli({"meta": _full_meta(fixed), "material": fixed})
        check(synced.returncode == 0,
              f"获准同步后应成功,实际 {synced.stderr or synced.stdout}")
        pending = read(PENDING_REL) or ""
        check("已同步" in pending and "缺同步授权" not in pending,
              f"完成同步后待同步记录须更新状态,实际 {pending}")


def test_check_failure_invalidates_dependent_recheck_results() -> None:
    """交付核验失败时,依赖失败对象的旧检查结果须作废;无关结果保留。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project, read, material, _applied = _run_full_flow(
            Path(tmp), material=_blocked_material())
        fixed = _resolved(material)
        plan = plan_delivery(_existing(project), _full_meta(fixed), fixed)
        check(plan["status"] == "planned",
              f"规划时应可整理,实际 {plan.get('status')}")
        (project / SPEC_REL).unlink()
        session = begin({
            "mode": "new_design", "stage": "只有设计，尚未实现",
            "goal": "完成每日挑战完整设计", "module": "每日挑战",
            "deps": [], "entry": DESIGN_REL,
            "authorization": {"write": True, "sync": True},
            "baseline": {DESIGN_REL: sha256_text(read(DESIGN_REL))},
        })["session"]
        session = record_read(session, SPEC_REL, "# 每日挑战:模块规格\n",
                              module="每日挑战", purpose="module",
                              call="交付前读取规格")["session"]
        session = record_read(session, PROJECT_REL,
                              read(PROJECT_REL) or "", module="每日挑战",
                              purpose="project",
                              call="交付前读取项目目标")["session"]
        session = remember(session, "规格完整性", {"ok": True},
                           depends_on=[SPEC_REL])["session"]
        session = remember(session, "无关检查", {"ok": True},
                           depends_on=[PROJECT_REL])["session"]
        applied = apply_delivery(plan, _Channel(svc, _handoff_token(svc)),
                                 read, session=session)
        check(applied.get("status") == "check_failed",
              f"规格被移除后不得标已保存,实际 {applied.get('status')}")
        result_session = applied.get("session") or {}
        check(reuse(result_session, "规格完整性") is None,
              "依赖被移除规格的旧检查结果须作废,不得继续报 ok=true")
        check(reuse(result_session, "无关检查") is not None,
              "不依赖失败对象的旧检查结果须保留,无需重查")
        ledger = [item for item in result_session.get("ledger") or []
                  if item.get("timing") == "invalidate"]
        check(any("断链" in str(item.get("check") or "") for item in ledger),
              f"台账须记录按失败对象作废,实际 {ledger}")


def test_cli_pending_completion_waits_for_checks() -> None:
    """检查失败时待同步记录不得提前写成已完成;检查通过后才更新。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project, read, material, _applied = _run_full_flow(
            root, material=_blocked_material())
        token = _handoff_token(svc)
        cli = str(SKILL_DIR / "full_design_cli.py")
        fixed = _resolved(material)

        def run_cli(meta, mat):
            return subprocess.run(
                [sys.executable, "-B", cli, "apply", "--project-root",
                 str(project), "--runtime-root", str(root / "runtime"),
                 "--token", token],
                input=json.dumps({"meta": meta, "material": mat},
                                 ensure_ascii=False),
                capture_output=True, text=True)

        no_sync = {"meta": {**_full_meta(fixed),
                            "authorization": {"write": True, "sync": False}},
                   "material": fixed}
        first = run_cli(no_sync["meta"], no_sync["material"])
        check(first.returncode == 0
              and json.loads(first.stdout).get("saved") is True,
              f"缺同步授权的待同步保存应成功,实际 {first.stdout}{first.stderr}")
        check("缺同步授权" in (read(PENDING_REL) or ""),
              "首次须写入待同步记录")

        broken = _resolved(material)
        content = dict(broken.get("content") or {})
        content["audio"] = [{
            "text": "新增配乐依据见 docs/ui-review-source-missing.md",
            "rules": ["daily-seed"]}]
        broken["content"] = content
        content_before_broken = read(CONTENT_REL)
        failed = run_cli(_full_meta(broken), broken)
        failed_result = json.loads(failed.stdout or "{}")
        check(failed.returncode == 1
              and failed_result.get("status") == "check_failed",
              f"引用缺失的授权同步须检查失败并非零退出,实际 {failed.stdout}")
        check(failed_result.get("states", {}).get("synced") is not True,
              "检查失败不得宣称已同步")
        pending_text = read(PENDING_REL) or ""
        check("已经完成" not in pending_text and "已同步" not in pending_text,
              f"检查失败时待同步记录不得宣布已完成,实际 {pending_text}")
        check("待同步" in pending_text,
              "失败时须保留可恢复的待同步事实")

        # 开发者修复内容文件后重试:检查通过,完成标记才更新。
        (project / CONTENT_REL).write_text(content_before_broken or "",
                                           encoding="utf-8")
        saved = run_cli(_full_meta(fixed), fixed)
        check(saved.returncode == 0,
              f"修复引用并重试应成功,实际 {saved.stderr or saved.stdout}")
        pending_text = read(PENDING_REL) or ""
        check("已同步" in pending_text and "缺同步授权" not in pending_text,
              f"检查通过后待同步记录须更新为已完成,实际 {pending_text}")


TESTS = (
    test_extracts_known_material_and_builds_coverage_map,
    test_scope_layers_and_template_fill_guard,
    test_stage_boundaries_follow_required_outcomes_not_round_count,
    test_journey_walkthrough_finds_existing_contradiction,
    test_full_flow_delivers_four_outputs_and_detects_planted_contradiction,
    test_delivery_detects_each_blocking_gap_without_false_completion,
    test_delivery_writes_only_with_authorization_and_keeps_existing_docs,
    test_cli_smoke_full_design_entry,
    test_skill_entry_documents_full_design_flow,
    test_missing_delivery_locations_keep_draft,
    test_after_write_check_failure_does_not_complete_delivery,
    test_missing_spec_file_keeps_delivery_incomplete,
    test_delivery_keeps_official_baseline_version_field,
    test_delivery_verify_failure_sets_checks_ok_false,
    test_second_required_module_spec_missing_keeps_delivery_incomplete,
    test_cli_pending_sync_record_continues_and_updates,
    test_check_failure_invalidates_dependent_recheck_results,
    test_cli_pending_completion_waits_for_checks,
)


def main() -> int:
    return run_theme("设计问答完整设计成稿", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())
