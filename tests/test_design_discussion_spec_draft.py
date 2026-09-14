#!/usr/bin/env python3
"""统一设计问答框架票 04:将模块决定整理为可交接规格。

接缝:``plugin/skills/game-design/spec_draft.py`` 的 ``plan_handoff`` /
``apply_handoff`` / ``verify_handoff``。固定小型模块(齿轮谜城每日挑战)与
现有历史决定夹具经票 03 的 ``decisions.py`` 真实受控通道落盘后,再核对
模块规格草稿、同步计划、版本与指纹处理、同步状态与交付边界。期望值来自
工单与规格字面量,只经公共接口观察行为,不测内部函数。

    python3 -B tests/test_design_discussion_spec_draft.py
"""

import json
import re
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

from checks import begin  # noqa: E402
from decision_records import sha256_text  # noqa: E402
from decisions import (  # noqa: E402
    apply_save, plan_save, plan_sync, restore_from_records,
)
from rounds import run_round  # noqa: E402
from spec_draft import apply_handoff, plan_handoff, verify_handoff  # noqa: E402

RECORD_REL = "docs/mygamestudio/records/decisions-每日挑战.md"
OTHER_RECORD_REL = "docs/mygamestudio/records/decisions-商业化.md"
SPEC_REL = "docs/mygamestudio/records/spec-每日挑战.md"
GLOSSARY_REL = "docs/mygamestudio/records/glossary.md"
DESIGN_REL = "docs/mygamestudio/GAME_DESIGN.md"
PROJECT_REL = "docs/mygamestudio/PROJECT.md"
TECH_REL = "docs/mygamestudio/TECH_DESIGN.md"
DATE = "2026-09-14"


def _service(root: Path):
    project = root / "project"
    (project / "docs/mygamestudio/records").mkdir(parents=True)
    (project / "docs/mygamestudio/GAME_DESIGN.md").write_text(
        "# 齿轮谜城:当前游戏需求与设计\n\n基线版本:v2。\n", encoding="utf-8")
    (project / "docs/mygamestudio/PROJECT.md").write_text(
        "# 项目目标\n\n当前版本只做主线 20 关。\n", encoding="utf-8")
    (project / "docs/mygamestudio/TECH_DESIGN.md").write_text(
        "# 技术设计\n\n存档为本地 JSON。\n", encoding="utf-8")
    (project / "docs/mygamestudio/CONFIG.md").write_text(
        "# 齿轮谜城:协作配置\n\n## 任务来源\n\n- 后端：local-markdown\n"
        "- 当前位置：work/\n\n## 标签映射\n\n| 语义 | 项目标签 |\n| --- | --- |\n"
        "| needs-triage | needs-triage |\n| needs-info | needs-info |\n"
        "| ready-for-agent | ready-for-agent |\n"
        "| ready-for-human | ready-for-human |\n| wontfix | wontfix |\n\n"
        "## 文档映射\n\n| 内容 | 当前权威位置 | 维护角色 |\n| --- | --- | --- |\n"
        f"| 项目目标与范围 | {PROJECT_REL} | 制作统筹 |\n"
        f"| 游戏需求与设计 | {DESIGN_REL} | 方案设计 |\n"
        f"| 技术设计 | {TECH_REL} | 制作实现 |\n"
        f"| 术语、ADR 与历史 | {GLOSSARY_REL} | 对应专业角色 |\n",
        encoding="utf-8")
    svc = GateService(root / "runtime")
    svc.init_policy(
        project_root=project,
        roles={"design": ["docs/mygamestudio/records/**", DESIGN_REL]},
        purposes={"design_discussion": ["docs/mygamestudio/records/**"],
                  "spec_sync": ["docs/mygamestudio/records/**", DESIGN_REL]},
    )
    return svc, project


def _baseline_check(project: Path) -> dict:
    """经仓库统一接口核对核心基线版本与双指纹(既有规则,不另算)。"""

    records_dir = PLUGIN_ROOT / "records"
    if str(records_dir) not in sys.path:
        sys.path.insert(0, str(records_dir))
    import mgs_records  # noqa: PLC0415

    return mgs_records.baseline_report(project)


def _design_entry(report: dict) -> dict:
    return next(item for item in report["docs"] if item["path"] == DESIGN_REL)


def _instance(svc, resources=None, purpose="design_discussion"):
    return svc.create_instance(
        role="design", task="G02", purpose=purpose,
        resources=list(resources or ["docs/mygamestudio/records/**"]),
        ttl_seconds=1800)


def _handoff_token(svc):
    """按同步授权创建实例:记录目录 + 核心基线的写入范围。"""

    return _instance(svc, resources=["docs/mygamestudio/records/**", DESIGN_REL],
                     purpose="spec_sync").token


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
        {"id": "Q5", "title": "商店定价", "body": "定价多少?",
         "options": {"A": "6 元", "B": "免费加广告"}, "recommendation": "A",
         "reason": "小体量一次买断更清楚。", "module": "商业化"},
    ]


def _turn(reply, *, round_no=1, settled=None, shown=None, proposals=None):
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
        "proposals": list(proposals or []),
    }


def _record_meta(*, round_no=1, reply="", write=True, module="每日挑战"):
    return {"record_path": RECORD_REL, "module": module, "round": round_no,
            "date": DATE, "decider": "开发者",
            "authorization": {"write": write}, "reply": reply}


def _sections():
    """固定小型模块的九类规格内容,全部按规格字面量给出具体规则与数值。"""

    return {
        "purpose": {
            "content": "让玩家每天用一次短局回到游戏;复用已有关卡,不新增内容制作。",
            "sources": ["Q1", "Q3"]},
        "participants": {
            "content": "玩家、每日关卡、每日种子、本机当日最佳记录;章节进度不受影响。",
            "sources": ["Q2"]},
        "triggers": {
            "content": "玩家从主菜单进入每日挑战时生效;当日关卡由本机日历日加固定种子确定。",
            "sources": ["Q3"]},
        "rules": {
            "content": "选择本机日期对应关卡 → 完成一局 → 按步数结算 → 更新当日最佳;每日只保留一个最佳值。",
            "sources": ["Q1", "Q4"]},
        "boundaries": {
            "content": "同日重复进行:只有更优成绩覆盖最佳;离线:直接使用本机日期;跨日:旧日最佳不再更新;失败或中途退出:不记录最佳。",
            "sources": ["Q4"]},
        "numbers": {
            "settled": [
                {"name": "每日关卡数量", "value": "1", "unit": "关/日",
                 "range": "1", "calc": "按日期索引现有 20 关",
                 "rounding": "向下取整",
                 "basis": "沿用现有 20 关,保证可复用"},
                {"name": "本机最佳记录条数", "value": "1", "unit": "条/日",
                 "range": "0-1", "calc": "每日只保留当日最佳",
                 "rounding": "不适用", "basis": "本机存档最小改动"},
            ],
            "trial": [
                {"name": "单局目标用步", "value": "40", "unit": "步",
                 "range": "30-60", "calc": "暂定目标",
                 "rounding": "不适用", "basis": "待原型试玩,试验值不作当前要求"},
            ],
            "sources": ["Q3", "Q4"]},
        "feedback": {
            "content": "进入时显示当日日期与当前最佳;结算后显示本次步数与最佳对比;未超过最佳时提示保持原记录。",
            "sources": ["Q4"]},
        "persistence": {
            "content": "保存每日种子与当日最佳步数;退出重进后当日最佳仍可读;跨日只读不回写旧日最佳。",
            "sources": ["Q4"]},
        "acceptance": {
            "cases": [
                {"initial": "新档,当日未玩",
                 "action": "从主菜单进入每日挑战并完成一局",
                 "expected": "记录当日最佳步数,再次进入可读"},
                {"initial": "当日已有最佳 42 步",
                 "action": "再玩一局 50 步",
                 "expected": "最佳仍是 42,并提示未超过"},
            ],
            "subjective": [
                {"question": "每日一局是否有重复游玩的动力",
                 "method": "原型内连续 3 天试玩并记录每日完成率",
                 "blocks_stage": False},
            ],
            "sources": ["Q4"]},
    }


def _meta(**over):
    write = over.pop("write", True)
    sync = over.pop("sync", True)
    meta = {
        "module": "每日挑战",
        "date": DATE,
        "record_path": RECORD_REL,
        "spec_path": SPEC_REL,
        "design_path": DESIGN_REL,
        "glossary_path": GLOSSARY_REL,
        "sync_ref": "GAME_DESIGN v3 / spec-每日挑战 v1",
        "version_from": "v2",
        "version_to": "v3",
        "change": "substantive",
        "authorization": {"write": write, "sync": sync},
        "sections": _sections(),
        "glossary": [],
        "adr": [],
        "scope_change": [],
        "verification": [],
        "proposals": [],
        "assumptions": [],
        "pending_impacts": {},
        "blocking_qids": [],
        "untouched": [PROJECT_REL, TECH_REL, OTHER_RECORD_REL],
        "doc_map": {"design": DESIGN_REL, "glossary": GLOSSARY_REL,
                    "records": "docs/mygamestudio/records"},
    }
    meta.update(over)
    return meta


def _existing(project, **over):
    """plan 所需的当前文件内容:规格/基线/术语表/无关资料的实际文本。"""

    def read(path):
        target = project / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    texts = {SPEC_REL: read(SPEC_REL), DESIGN_REL: read(DESIGN_REL),
             GLOSSARY_REL: read(GLOSSARY_REL), PROJECT_REL: read(PROJECT_REL),
             TECH_REL: read(TECH_REL), OTHER_RECORD_REL: read(OTHER_RECORD_REL)}
    texts.update(over)
    return texts


def _save_record(channel, read, rounds, sync_qids=(), owner=None):
    """经票 03 真实受控通道把历史决定夹具落到实际记录文件。

    ``owner`` 给出夹具保存所用的实例,夹具完成后按运行保障的占用纪律释放
    执行能力并回收占用,后续交接由另一个实例承接(与真实会话一致)。
    """

    settled = {}
    for index, (reply, shown) in enumerate(rounds, start=1):
        turn = _turn(reply, round_no=index, settled=dict(settled),
                     shown=list(shown))
        result = run_round(turn)
        applied = apply_save(
            plan_save(read(RECORD_REL), result,
                      _record_meta(round_no=index, reply=reply)),
            channel, read)
        check(applied["status"] in {"saved", "no_new"},
              f"夹具第 {index} 轮决定应实际落盘,实际 {applied['status']}")
        settled.update({qid: item["value"]
                        for qid, item in result["adopted"].items()})
    if sync_qids:
        record_text = read(RECORD_REL)
        synced = apply_save(
            plan_sync(record_text, {
                "record_path": RECORD_REL, "module": "每日挑战",
                "date": DATE, "qids": list(sync_qids),
                "sync_ref": "GAME_DESIGN v2",
                "authorization": {"write": True, "sync": True}}),
            channel, read)
        check(synced["status"] == "saved",
              f"夹具预同步应成功,实际 {synced['status']}")
    if owner is not None:
        channel.svc.release_instance(owner.instance_id)
        channel.svc.reclaim_locks(owner.instance_id)
    return read(RECORD_REL)


def test_full_module_handoff_from_adopted_decisions() -> None:
    """收敛:汇总已采纳未同步决定,九类规格齐全,按授权同步受影响基线。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        channel = _Channel(svc, _handoff_token(svc))
        read = _reader(project)
        _seed_glossary(project)
        before_project = read(PROJECT_REL)
        before_tech = read(TECH_REL)
        _save_record(save_channel, read, (
            ("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),
            ("Q3 选 A", ["Q3"]),
            ("Q1 调整为 从现有 20 关按日期抽取", ["Q4"]),
        ), sync_qids=("Q2",), owner=save_owner)
        meta = _meta(glossary=[
            {"term": "每日种子",
             "meaning": "由本机日历日加固定种子得到的关卡选择依据。",
             "source": "Q3"},
            {"term": "每日挑战入口",
             "meaning": "与章节并存的主菜单入口,不替代章节。", "source": "Q2"},
        ], adr=[
            {"title": "每日挑战与章节并存", "change_cost_high": True,
             "confusing_without_context": True, "real_tradeoff": True,
             "background": "并存保证已有关卡不被替换,代价是主菜单多一个入口。"},
            {"title": "每日关复用现有 20 关", "change_cost_high": False,
             "confusing_without_context": True, "real_tradeoff": True,
             "background": "复用最省制作,但后续换关需重新选材。"},
        ], pending_impacts={"Q4": "影响本机存档结构,不阻断当前交接;"},
            proposals=["联网排行榜：Q4 的候选选项 B,保持候选身份"],
            verification=[{"question": "每日一局是否有重复游玩的动力",
                           "method": "原型内连续 3 天试玩并记录每日完成率",
                           "blocks_stage": False}])
        plan = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                            _existing(project))
        check(plan["status"] == "planned", f"收敛模块应可交接,实际 {plan.get('status')}:{plan.get('gaps')}")
        check(plan["to_sync"] == ["Q1", "Q3"] and plan["synced"] == ["Q2"],
              f"只汇总已采纳且未同步的决定,实际 {plan['to_sync']}/{plan['synced']}")
        check(plan["version"] == {"from": "v2", "to": "v3",
                                  "change": "substantive",
                                  "note": plan["version"]["note"]}
              and "实质" in plan["version"]["note"],
              f"实质变化须递增版本,实际 {plan['version']}")
        text = plan["spec"]["content"]
        for heading in ("## 设计目的", "## 参与对象", "## 前提与触发",
                        "## 正常规则", "## 例外与边界", "## 数值与配置",
                        "## 玩家反馈", "## 数据与持续性", "## 验收方式"):
            check(heading in text, f"模块规格须按适用性说明 {heading}")
        for needle in (
            "本机日历日加固定种子",
            "### 已定值", "### 候选试验值",
            "取整 向下取整", "依据 沿用现有 20 关",
            "### 验收场景",
            "初始条件：新档,当日未玩", "操作：从主菜单进入每日挑战并完成一局",
            "预期结果：记录当日最佳步数",
            "是否阻断当前阶段：否",
            "Q4 记录：未回答", "影响：影响本机存档结构,不阻断当前交接",
            "旧值「B 每日生成新关」", "已被第 3 轮替代",
            "来源 开发者逐题选择（第 1 轮）",
            "未实现（设计交接不自动授权制作,不自动启动制作）",
            "未验证（没有原型或试玩证据",
            "## 未采纳内容", "联网排行榜", "候选试验值", "单局目标用步",
            "## 重要决定背景", "每日挑战与章节并存",
        ):
            check(needle in text, f"模块规格草稿应包含 {needle!r}")
        check("复用现有 20 关：复用最省制作" not in text.split(
            "## 重要决定背景")[-1],
            "只有三项条件同时成立的决定才单独记录背景")
        check("每日关复用现有 20 关" in plan["adr_rejected"][0]["detail"],
              f"未满足条件的决定背景须如实说明,实际 {plan.get('adr_rejected')}")
        check("联网排行榜" not in text.split("## 未采纳内容")[0],
              "候选方案不得写成当前要求")
        check("待同步" in text or "同步" in text,
              "规格须写明决定记录的同步状态位置")

        applied = apply_handoff(plan, channel, read)
        check(applied["status"] == "saved" and applied["saved"] is True,
              f"获准交接应实际落盘,实际 {applied}")
        check(set(applied["written"]) == {SPEC_REL, DESIGN_REL, GLOSSARY_REL,
                                          RECORD_REL},
              f"只同步实际受影响的规格、基线与术语表,实际 {applied['written']}")
        check(read(SPEC_REL) == text, "模块规格须与计划内容一致并回读")
        design = read(DESIGN_REL)
        check("v3" in design and SPEC_REL in design,
              f"核心基线须递增版本并引用模块规格,实际 {design}")
        check("跨日" not in design and "单局目标用步" not in design,
              "具体规则集中维护在模块规格,基线不重复规则正文")
        record = read(RECORD_REL)
        check("同步状态：已同步（2026-09-14，GAME_DESIGN v3 / spec-每日挑战 v1）"
              in record and "同步状态：待同步" not in record,
              f"按授权同步须逐项落盘,实际 {record}")
        check("B 每日生成新关（已被替代）" in record
              and "替代：「B 每日生成新关」" in record,
              "历史与替代关系须保留")
        glossary = read(GLOSSARY_REL)
        check("步数：玩家一次移动算一步。来源：既有术语表。" in glossary
              and "每日种子" in glossary and "每日挑战入口" in glossary,
              f"术语表须保留既有条目并补充已明确术语,实际 {glossary}")
        check(read(PROJECT_REL) == before_project
              and read(TECH_REL) == before_tech
              and read(OTHER_RECORD_REL) is None,
              "无关管理资料与其他模块不得改动")
        check(applied["states"]["saved"] is True
              and applied["states"]["synced"] is True
              and applied["states"]["implemented"] is False
              and applied["states"]["verified"] is False,
              f"已保存/已同步/未实现/未验证须分开,实际 {applied['states']}")
        check(applied["to_sync"] == [] and "待同步：无" in applied["report"],
              f"同步后不得再有待同步项,实际 {applied.get('to_sync')}")
        check("本次只交接模块" in applied["report"]
              and "未验证" in applied["report"] and "未实现" in applied["report"],
              f"报告须区分模块可交接与整体完成,实际 {applied['report']}")
        check(plan["producer_handoff"] is None,
              "无目标或范围变化时不输出统筹同步交接")
        baseline = _baseline_check(project)
        entry = _design_entry(baseline)
        check(entry["status"] == "一致" and entry["declared_version"] == "v3",
              f"基线版本与双指纹须按既有规则登记并一致,实际 {entry}")
        verdict = verify_handoff(plan, {
            SPEC_REL: read(SPEC_REL), DESIGN_REL: read(DESIGN_REL),
            GLOSSARY_REL: read(GLOSSARY_REL), RECORD_REL: read(RECORD_REL),
            PROJECT_REL: read(PROJECT_REL), TECH_REL: read(TECH_REL)})
        check(verdict["ok"], f"回读核对应通过,实际 {verdict}")


def _missing_sections(*drop):
    sections = {name: {**entry} for name, entry in _sections().items()}
    for name in drop:
        sections.pop(name, None)
    return sections


def test_missing_key_content_reports_incomplete_without_defaults() -> None:
    """关键字段缺失:准确报告未完成,不用默认值补齐阻断交接的缺口。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        read = _reader(project)
        _seed_glossary(project)
        _save_record(save_channel, read,
                     (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),),
                     owner=save_owner)
        sections = _missing_sections("rules")
        sections["rules"] = {"content": "", "sources": ["Q1"]}
        meta = _meta(sections=sections, blocking_qids=["Q4"])
        plan = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                            _existing(project))
        check(plan["status"] == "incomplete",
              f"关键行为缺口须报告未完成,实际 {plan['status']}")
        check(plan["saved"] is False and plan["content"] is None,
              "未完成时不得产出可落盘规格")
        check(plan["missing"] and plan["missing"][0]["field"] == "rules",
              f"须逐项指出缺失的关键内容,实际 {plan['missing']}")
        check(any("正常规则" in item["detail"] for item in plan["missing"]),
              f"缺口说明须点到具体规格类别,实际 {plan['missing']}")
        check(plan["blocking"] == ["Q4"] and plan["handoffable"] is False,
              f"阻断当前交接的未决项须如实列出,实际 {plan.get('blocking')}")
        check("未完成" in plan["report"] and "不用默认值" in plan["report"],
              f"报告须说明未完成且不补默认值,实际 {plan['report']}")
        applied = apply_handoff(plan, _Channel(svc, _handoff_token(svc)), read)
        check(applied["saved"] is False and applied["written"] == [],
              f"未完成模块不得写入任何文件,实际 {applied}")
        check(read(SPEC_REL) is None and read(DESIGN_REL) ==
              _service_design_text(), "未完成交接不得改动规格或基线")

        vague = _sections()
        vague["rules"] = {"content": "规则合理、强度适中即可。",
                          "sources": ["Q1"]}
        plan2 = plan_handoff({RECORD_REL: read(RECORD_REL)},
                             _meta(sections=vague, blocking_qids=["Q4"]),
                             _existing(project))
        check(plan2["status"] == "incomplete"
              and any("形容词" in item["detail"]
                      or "不可检查" in item["detail"]
                      for item in plan2["missing"]),
              f"以「合理、适中」代替关键行为时须报告未完成,实际 {plan2['missing']}")

        # 不适用须有理由:给出理由的类别不判缺口,空占位判缺口
        na_sections = _missing_sections()
        na_sections["persistence"] = {"content": "",
                                      "not_applicable": "本模块无跨次游玩保存,"
                                                        "复用本机既有存档;"
                                                        "依据 Q4 未决项。",
                                      "sources": ["Q4"]}
        plan3 = plan_handoff({RECORD_REL: read(RECORD_REL)},
                             _meta(sections=na_sections, blocking_qids=[],
                                   pending_impacts={
                                       "Q4": "影响本机存档结构,不阻断当前交接;"}),
                             _existing(project))
        check(plan3["status"] == "planned",
              f"不适用有理由时应视为已说明,实际 {plan3.get('missing')}")
        check("不适用：本模块无跨次游玩保存" in plan3["spec"]["content"],
              "不适用理由须写入规格")


def _service_design_text() -> str:
    return "# 齿轮谜城:当前游戏需求与设计\n\n基线版本:v2。\n"


def test_format_only_change_does_not_claim_new_version() -> None:
    """纯格式调整不冒充新产品要求:语义未变时不递增版本,基线不动。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        channel = _Channel(svc, _handoff_token(svc))
        read = _reader(project)
        _seed_glossary(project)
        _save_record(save_channel, read,
                     (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),),
                     sync_qids=("Q1", "Q2"), owner=save_owner)
        meta = _meta(pending_impacts={"Q3": "等待补充;", "Q4": "影响存档结构;"},
                     blocking_qids=[])
        first = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                            _existing(project))
        check(first["status"] == "planned" and first["spec"]["content"],
              f"首次整理应产出规格,实际 {first.get('status')}")
        (project / SPEC_REL).write_text(_degrade_format(first["spec"]["content"]),
                                        encoding="utf-8")
        before_design = read(DESIGN_REL)
        before_record = read(RECORD_REL)
        before_glossary = read(GLOSSARY_REL)
        plan = plan_handoff({RECORD_REL: read(RECORD_REL)},
                            {**meta, "change": "substantive",
                             "version_from": "v2", "version_to": "v3"},
                            _existing(project))
        check(plan["status"] == "planned",
              f"现有规格可继续整理,实际 {plan.get('status')}:{plan.get('gaps')}")
        check(plan["compare"]["previous_present"] is True
              and plan["compare"]["semantic_equal"] is True,
              f"须回读核对新旧规则是否同一语义,实际 {plan['compare']}")
        check(plan["version"]["change"] == "format"
              and plan["version"]["from"] == "v2"
              and plan["version"]["to"] == "v2",
              f"语义未变时不得递增版本,实际 {plan['version']}")
        check("格式" in plan["version"]["note"]
              and "新产品要求" in plan["version"]["note"],
              f"版本说明须区分格式修正与新产品要求,实际 {plan['version']['note']}")
        check(any("语义一致" in item for item in plan["warnings"]),
              f"声明与回读不符须如实提示,实际 {plan.get('warnings')}")
        applied = apply_handoff(plan, channel, read)
        check(applied["status"] == "saved" and applied["written"] == [SPEC_REL],
              f"格式修正只改规格本身,实际 {applied.get('written')}")
        check(read(DESIGN_REL) == before_design,
              "格式修正不得改写核心基线版本")
        check("v2" in read(DESIGN_REL) and "v3" not in read(DESIGN_REL),
              "基线版本保持 v2")
        check(read(RECORD_REL) == before_record
              and read(GLOSSARY_REL) == before_glossary,
              "格式修正不得改动决定记录与术语表")
        check(read(SPEC_REL) == plan["spec"]["content"]
              and "## 设计目的" in read(SPEC_REL),
              "格式修正须按标准结构落盘")
        check("不算新产品要求" in applied["report"]
              and "版本保持" in applied["report"],
              f"报告须说明格式修正不触发新版本,实际 {applied['report']}")


def test_read_only_and_missing_sync_authorization_keep_pending() -> None:
    """只读与缺同步授权:不写入,待同步项与未决影响如实保留。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        read = _reader(project)
        _seed_glossary(project)
        _save_record(save_channel, read,
                     (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),),
                     owner=save_owner)
        meta = _meta(pending_impacts={"Q3": "等待补充;", "Q4": "影响存档结构;",
                                      "Q1": "复用方式;", "Q2": "入口数量;"},
                     blocking_qids=[])
        read_only = plan_handoff({RECORD_REL: read(RECORD_REL)},
                                 {**meta, "authorization": {"write": False}},
                                 _existing(project))
        check(read_only["status"] == "read_only",
              f"无写入授权时只读,实际 {read_only['status']}")
        check(read_only["saved"] is False and read_only["spec"]["content"],
              "只读仍给出草稿内容,但不得称已保存")
        blocked = apply_handoff(read_only, _Channel(svc, _handoff_token(svc)),
                                read)
        check(blocked["saved"] is False and blocked["written"] == [],
              f"只读不得写入任何文件,实际 {blocked}")
        check("未保存" in blocked["report"] and "未同步" in blocked["report"],
              f"只读报告须说明未保存未同步,实际 {blocked['report']}")
        check(read(SPEC_REL) is None, "只读不得留下规格文件")
        check(read(GLOSSARY_REL) == _seeded_glossary_text(),
              "只读不得改动术语表")

        unsynced = plan_handoff({RECORD_REL: read(RECORD_REL)},
                                {**meta, "authorization": {"write": True,
                                                           "sync": False}},
                                _existing(project))
        check(unsynced["status"] == "planned"
              and unsynced["sync_authorized"] is False,
              f"缺同步授权仍可整理规格,实际 {unsynced['status']}")
        applied = apply_handoff(unsynced, _Channel(svc, _handoff_token(svc)),
                                read)
        check(applied["saved"] is True and applied["written"] == [SPEC_REL],
              f"缺同步授权时只写规格,实际 {applied.get('written')}")
        check(applied["to_sync"] == ["Q1", "Q2"]
              and applied["states"]["synced"] is False,
              f"待同步项须原样保留并可定位,实际 {applied['to_sync']}")
        check("待同步" in applied["report"]
              and "同步授权" in applied["report"],
              f"报告须说明缺同步授权,实际 {applied['report']}")
        state = restore_from_records({RECORD_REL: read(RECORD_REL)}, "每日挑战")
        check(state["to_sync"] == ["Q1", "Q2"],
              f"记录中的同步状态不得被推定,实际 {state['to_sync']}")
        check(read(RECORD_REL).count("同步状态：待同步") == 2,
              "未经授权的同步不得改动记录")


def _seeded_glossary_text() -> str:
    return "# 术语表\n\n- 步数：玩家一次移动算一步。来源：既有术语表。\n"


def _seed_glossary(project: Path) -> None:
    (project / GLOSSARY_REL).write_text(_seeded_glossary_text(),
                                        encoding="utf-8")


def _degrade_format(text: str) -> str:
    """仅改排版(标题层级与空行),语义文字逐字不变。"""

    return text.replace("\n## ", "\n### ").replace("\n\n", "\n\n\n")


def test_history_pending_and_unrelated_content_preserved() -> None:
    """历史、未决与无关内容不变:改口历史保留,其他模块与资料零改动。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        read = _reader(project)
        _seed_glossary(project)
        (project / OTHER_RECORD_REL).write_text(
            "# 商业化：决定记录\n\n- D 商业化·Q5 商店定价：采纳 A 6 元\n",
            encoding="utf-8")
        before_other = read(OTHER_RECORD_REL)
        before_project = read(PROJECT_REL)
        before_tech = read(TECH_REL)
        before_glossary = read(GLOSSARY_REL)
        _save_record(save_channel, read, (
            ("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),
            ("Q1 调整为 从现有 20 关按日期抽取", ["Q4"]),
        ), owner=save_owner)
        plan = plan_handoff({RECORD_REL: read(RECORD_REL)},
                            _meta(pending_impacts={"Q3": "等待补充;",
                                                   "Q4": "影响存档结构;"},
                                  blocking_qids=[]),
                            _existing(project))
        check(plan["status"] == "planned", f"应可交接,实际 {plan.get('status')}")
        text = plan["spec"]["content"]
        check("旧值「B 每日生成新关」" in text
              and "已被第 2 轮替代" in text,
              "替代关系与历史须保留在规格草稿中")
        check(plan["to_sync"] == ["Q1", "Q2"] and plan["superseded"] == ["Q1"],
              f"改口后只列当前有效且未同步的决定,实际 {plan}")
        check("Q3 每日身份" in text and "Q4 记录" in text
              and "未决与延期事项" in text,
              "未决项须保留在规格草稿中")
        check("Q4 记录" in plan["report"]
              and "影响：影响存档结构" in plan["report"],
              f"报告须列出未决项与影响,实际 {plan['report']}")
        check(OTHER_RECORD_REL in plan["untouched"]
              and PROJECT_REL in plan["untouched"],
              f"须声明不受影响的范围,实际 {plan['untouched']}")
        applied = apply_handoff(plan, _Channel(svc, _handoff_token(svc)), read)
        check(applied["saved"] is True, f"交接应落盘,实际 {applied}")
        check(read(OTHER_RECORD_REL) == before_other,
              "其他模块的决定记录不得改动")
        check(read(PROJECT_REL) == before_project,
              "无关管理资料不得改动")
        check(read(TECH_REL) == before_tech, "技术设计不在授权范围")
        check(read(GLOSSARY_REL) == before_glossary,
              "没有新术语时术语表不得改动")
        check("其他模块与无关资料不变" not in applied["report"]
              or OTHER_RECORD_REL in applied["report"],
              f"报告须如实说明同步范围,实际 {applied['report']}")
        record = read(RECORD_REL)
        check("B 每日生成新关（已被替代）" in record
              and "替代：「B 每日生成新关」（第 1 轮，历史保留）" in record,
              "决定记录的改口历史不得丢失")


def test_handoff_states_stay_separate_from_implementation_and_playtest() -> None:
    """模块可交接不等于全游戏完成或体验已验证;无证据不报验证通过。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        read = _reader(project)
        _seed_glossary(project)
        _save_record(save_channel, read,
                     (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),),
                     owner=save_owner)
        meta = _meta(pending_impacts={"Q3": "等待补充;", "Q4": "影响存档结构;"},
                     blocking_qids=[],
                     verification=[{"question": "每日一局是否有重复游玩的动力",
                                    "method": "原型内连续 3 天试玩并记录每日完成率",
                                    "blocks_stage": True}])
        plan = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                            _existing(project))
        text = plan["spec"]["content"]
        check("是否阻断当前阶段：是" in text,
              f"主观体验须标明是否阻断当前阶段,实际 {text}")
        check("验证问题：每日一局是否有重复游玩的动力" in text
              and "验证方法：原型内连续 3 天试玩并记录每日完成率" in text,
              "主观体验须列出验证问题与方法")
        check("不自动启动制作" in text and "未验证" in text,
              "规格须标明未验证且不自动开始制作")
        check(plan["states"] == {"adopted": True, "synced": False,
                                 "implemented": False, "verified": False},
              f"分档状态不得混同,实际 {plan['states']}")
        applied = apply_handoff(plan, _Channel(svc, _handoff_token(svc)), read)
        check(applied["states"]["verified"] is False
              and applied["states"]["implemented"] is False,
              "没有原型或试玩证据时不得报告实现或体验验证通过")
        check("未实现" in applied["report"] and "未验证" in applied["report"],
              f"报告须分别标明未实现与未验证,实际 {applied['report']}")
        check(applied["blocking_verification"]
              == ["每日一局是否有重复游玩的动力"],
              f"阻断当前阶段的验证问题须单列,实际 {applied.get('blocking_verification')}")


def test_scope_change_hands_off_without_writing_management_docs() -> None:
    """目标或范围变化:交制作统筹同步,不扩权代写管理资料。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        read = _reader(project)
        _seed_glossary(project)
        _save_record(save_channel, read,
                     (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),),
                     owner=save_owner)
        before_project = read(PROJECT_REL)
        meta = _meta(pending_impacts={"Q3": "等待补充;", "Q4": "影响存档结构;"},
                     blocking_qids=[],
                     scope_change=[{"content": "每日挑战成为首发范围的一部分",
                                    "impact": "超出 PROJECT 当前包含的主线 20 关",
                                    "action": "显式调用 Game-Producer 完成变更同步"}])
        plan = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                            _existing(project))
        check(plan["producer_handoff"]
              and plan["producer_handoff"]["items"][0]["content"]
              == "每日挑战成为首发范围的一部分",
              f"触及目标或范围时须输出统筹同步交接,实际 {plan.get('producer_handoff')}")
        check("Game-Producer" in plan["producer_handoff"]["action"],
              "交接须给出建议动作")
        applied = apply_handoff(plan, _Channel(svc, _handoff_token(svc)), read)
        check(applied["saved"] is True, f"规格交接本身仍应完成,实际 {applied}")
        check(read(PROJECT_REL) == before_project,
              "管理资料不得被代写")
        check(PROJECT_REL in applied["untouched"]
              and "统筹同步交接" in applied["report"],
              f"报告须说明范围变化交统筹处理,实际 {applied['report']}")


def test_cli_smoke_handoff_entry() -> None:
    """CLI 冒烟:经真实受控通道按固定会话顺序覆盖完整交接与失败场景。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        read = _reader(project)
        _seed_glossary(project)
        token = _handoff_token(svc)
        cli = str(SKILL_DIR / "spec_draft_cli.py")
        _save_record(save_channel, read, (
            ("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),
            ("Q1 调整为 从现有 20 关按日期抽取", ["Q4"]),
        ), owner=save_owner)

        def run_cli(action, payload, *args, token=token):
            return subprocess.run(
                [sys.executable, "-B", cli, action, "--project-root",
                 str(project), "--runtime-root", str(root / "runtime"),
                 "--token", token, *args],
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True, text=True)

        # 1) 完整交接:整理 → 经通道落盘 → 回读核对
        payload = {"records": {RECORD_REL: read(RECORD_REL)}, "meta": _meta(
            pending_impacts={"Q3": "等待补充;", "Q4": "影响存档结构;"},
            blocking_qids=[])}
        planned = run_cli("plan", payload)
        check(planned.returncode == 0, f"CLI plan 应成功,实际 {planned.stderr}")
        plan = json.loads(planned.stdout)
        check(plan["status"] == "planned", f"CLI plan 应给出计划,实际 {plan}")
        saved = run_cli("apply", payload)
        check(saved.returncode == 0, f"CLI apply 应成功,实际 {saved.stderr}")
        applied = json.loads(saved.stdout)
        check(applied["status"] == "saved" and applied["saved"] is True,
              f"CLI 应经受控通道落盘,实际 {applied['status']}")
        check(set(applied["written"]) == {SPEC_REL, DESIGN_REL, RECORD_REL},
              f"CLI 冒烟须留实际落盘文件作证,实际 {applied['written']}")
        record_text = read(RECORD_REL)
        check("同步状态：已同步" in record_text
              and "同步状态：待同步" not in record_text,
              "CLI 交接须把同步状态写入实际记录")

        # 2) 回读核对:verify 只读核对既有交付
        verify_out = run_cli("verify", {"records": {RECORD_REL: read(RECORD_REL)},
                                        "meta": _meta(
                                            pending_impacts={
                                                "Q3": "等待补充;",
                                                "Q4": "影响存档结构;"},
                                            blocking_qids=[])})
        check(verify_out.returncode == 0, f"CLI verify 应成功,实际 {verify_out.stderr}")
        verdict = json.loads(verify_out.stdout)
        check(verdict["ok"] is True, f"CLI verify 须回读核对,实际 {verdict}")

        # 3) 关键缺口:报告未完成并以非零码退出,不写任何文件
        before_spec = read(SPEC_REL)
        gaps = _meta(sections=_missing_sections("rules"), blocking_qids=["Q4"],
                     pending_impacts={"Q4": "影响存档结构;"})
        failed = run_cli("apply", {"records": {RECORD_REL: read(RECORD_REL)},
                                   "meta": gaps})
        check(failed.returncode == 1, f"缺口须以非零码报告,实际 {failed.returncode}")
        gap_result = json.loads(failed.stdout)
        check(gap_result["status"] == "incomplete"
              and gap_result["saved"] is False,
              f"缺口须报告未完成,实际 {gap_result['status']}")
        check(read(SPEC_REL) == before_spec, "未完成不得改动既有规格")

        # 4) 只读:未授权时不写入
        read_only = run_cli("apply", {"records": {RECORD_REL: read(RECORD_REL)},
                                      "meta": _meta(
                                          write=False,
                                          pending_impacts={
                                              "Q3": "等待补充;",
                                              "Q4": "影响存档结构;"},
                                          blocking_qids=[])})
        check(read_only.returncode == 1,
              f"未授权写入应以非零码退出,实际 {read_only.returncode}")
        check(json.loads(read_only.stdout)["status"] == "read_only",
              "未授权时须报告只读")
        check(read(SPEC_REL) == before_spec, "只读不得改动规格")

        # 5) 越界:授权外写入被受控通道拒绝,原样报告依据
        before_design = read(DESIGN_REL)
        limited = _instance(svc, resources=["docs/mygamestudio/records/**"],
                            purpose="design_discussion").token
        denied = run_cli("apply", {"records": {RECORD_REL: read(RECORD_REL)},
                                   "meta": _meta(
                                       pending_impacts={"Q3": "等待补充;",
                                                        "Q4": "影响存档结构;"},
                                       blocking_qids=[])}, token=limited)
        check(denied.returncode == 1 and json.loads(
            denied.stdout)["status"] == "denied",
            f"授权外基线写入须被拒,实际 {denied.stdout}")
        check("task_grant" in denied.stdout and "未保存" in denied.stdout,
              f"拒绝须给出真实依据,实际 {denied.stdout}")
        check(read(DESIGN_REL) == before_design,
              "被拒后基线不得出现半写状态")

    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("spec_draft.py", "spec_draft_cli.py", "plan_handoff",
                   "apply_handoff", "九类", "Game-Spec", "统筹同步交接",
                   "未完成", "候选试验值", "不自动启动制作", "回读"):
        check(needle in text, f"Game-Design 入口须说明 {needle}")
    spec_skill = (PLUGIN_ROOT / "skills" / "game-spec" / "SKILL.md").read_text(
        encoding="utf-8")
    for needle in ("模块规格", "版本", "指纹", "格式修正", "统筹同步交接"):
        check(needle in spec_skill, f"Game-Spec 入口须覆盖 {needle}")


def test_revised_decision_is_not_inherited_as_synced() -> None:
    """改口后的决定从待同步重新开始,不继承旧要求的已同步状态。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        read = _reader(project)
        _seed_glossary(project)
        # 首轮保存后在第 2 轮改口 Q1,再只同步 Q2:改口的决定不得继承旧同步状态
        _save_record(save_channel, read,
                     (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),))
        record = read(RECORD_REL)
        revised = run_round(_turn("Q1 调整为 从现有 20 关按日期抽取",
                                  round_no=2,
                                  settled={"Q1": "B 每日生成新关",
                                           "Q2": "B 与章节并存"},
                                  shown=["Q4"]))
        applied_revision = apply_save(
            plan_save(record, revised,
                      _record_meta(round_no=2,
                                   reply="Q1 调整为 从现有 20 关按日期抽取")),
            save_channel, read)
        check(applied_revision["status"] == "saved",
              f"改口保存应成功,实际 {applied_revision['status']}")
        synced = apply_save(
            plan_sync(read(RECORD_REL), {
                "record_path": RECORD_REL, "module": "每日挑战",
                "date": DATE, "qids": ["Q2"], "sync_ref": "GAME_DESIGN v2",
                "authorization": {"write": True, "sync": True}}),
            save_channel, read)
        check(synced["status"] == "saved", f"夹具同步应成功,实际 {synced}")
        save_channel.svc.release_instance(save_owner.instance_id)
        save_channel.svc.reclaim_locks(save_owner.instance_id)
        record = read(RECORD_REL)
        state = restore_from_records({RECORD_REL: record}, "每日挑战")
        check(state["to_sync"] == ["Q1"],
              f"改口后的决定须重新待同步,实际 {state['to_sync']}")
        check(state["decisions"]["Q1"]["synced"] is False,
              "旧要求的已同步状态不得继承给新要求")
        plan = plan_handoff({RECORD_REL: record},
                            _meta(pending_impacts={"Q3": "等待补充;",
                                                  "Q4": "影响存档结构;"},
                                  blocking_qids=[]),
                            _existing(project))
        check(plan["to_sync"] == ["Q1"] and plan["synced"] == ["Q2"],
              f"规格汇总须只列真正待同步的决定,实际 {plan['to_sync']}")
        applied = apply_handoff(plan, _Channel(svc, _handoff_token(svc)), read)
        check(applied["status"] == "saved" and applied["states"]["synced"],
              f"同步后应为已同步,实际 {applied.get('states')}")
        final = read(RECORD_REL)
        check("不适用（已被替代" in final and "同步状态：待同步" not in final,
              f"历史决定的同步状态不得留成待同步,实际 {final}")


def _rich_baseline() -> str:
    """现行基线含其他模块规则与引用,交接每日挑战时必须保留。"""

    return (
        "# 齿轮谜城：当前游戏需求与设计\n\n"
        "维护责任：方案设计。基线版本：v2。适用范围：全游戏。\n\n"
        "## 章节模式\n\n"
        "- 章节按关卡顺序解锁。\n"
        "- 规则引用：docs/mygamestudio/records/spec-章节.md\n\n"
        "## 商业化\n\n"
        "- 只做广告变现，禁止付费入口。\n\n"
        "内容指纹：sha256:" + "0" * 64 + "\n"
        "归一指纹：sha256:" + "0" * 64 + "\n")


def _handoff_fixture(project, svc, *, sections=None, change="substantive"):
    save_owner = _instance(svc)
    save_channel = _Channel(svc, save_owner.token)
    read = _reader(project)
    _seed_glossary(project)
    _save_record(save_channel, read,
                 (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),),
                 owner=save_owner)
    meta = _meta(sections=sections or _sections(), change=change,
                 pending_impacts={"Q3": "等待补充;", "Q4": "影响存档结构;"},
                 blocking_qids=[])
    return read, meta, _Channel(svc, _handoff_token(svc))


def test_module_sync_keeps_unrelated_baseline_rules() -> None:
    """同步一个模块时,其他模块现行规则与引用必须保留。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        (project / DESIGN_REL).write_text(_rich_baseline(), encoding="utf-8")
        read, meta, channel = _handoff_fixture(project, svc)
        plan = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                            _existing(project))
        check(plan["status"] == "planned",
              f"可交接模块应进入计划,实际 {plan.get('status')}:{plan.get('gaps')}")
        applied = apply_handoff(plan, channel, read)
        check(applied["status"] == "saved", f"获准交接应落盘,实际 {applied}")
        design = read(DESIGN_REL)
        check("章节按关卡顺序解锁" in design,
              f"章节规则须保留,实际 {design}")
        check("docs/mygamestudio/records/spec-章节.md" in design,
              "其他模块规格引用不得随本次交接消失")
        check("只做广告变现，禁止付费入口" in design,
              "商业化现行规则不得随本次交接消失")
        check(SPEC_REL in design and "v3" in design,
              f"本次模块规格引用与新版本须写入,实际 {design}")
        verdict = verify_handoff(plan, {
            SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
            GLOSSARY_REL: read(GLOSSARY_REL), RECORD_REL: read(RECORD_REL)})
        check(verdict["ok"], f"保留既有基线后回读仍应通过,实际 {verdict}")


def test_format_claim_blocks_when_semantics_changed() -> None:
    """声明格式修正但规则实质变化时,不得按格式修正保存。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        read, meta, channel = _handoff_fixture(project, svc)
        first = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                             _existing(project))
        check(first["status"] == "planned", f"首次整理应产出规格,实际 {first}")
        (project / SPEC_REL).write_text(first["spec"]["content"],
                                        encoding="utf-8")
        before_design = read(DESIGN_REL)
        mutated = _sections()
        mutated["rules"] = {
            "content": "选择本机日期对应关卡 → 完成一局 → 按步数结算 → "
                       "更新当日最佳;每日保留三个最佳值。",
            "sources": ["Q1", "Q4"]}
        plan = plan_handoff(
            {RECORD_REL: read(RECORD_REL)},
            {**meta, "change": "format", "sections": mutated},
            _existing(project))
        check(plan["status"] != "planned" and plan.get("saved") is not True,
              f"声明与实质内容矛盾时不得进入同步,实际 {plan.get('status')}")
        check(plan["compare"]["semantic_equal"] is False,
              f"回读须检出实质变化,实际 {plan.get('compare')}")
        applied = apply_handoff(plan, channel, read)
        check(applied["saved"] is not True and applied.get("written") in (None, []),
              f"矛盾未解决前不得写入,实际 {applied}")
        check(read(DESIGN_REL) == before_design,
              "格式声明与实质变化冲突时不得改写核心基线")
        check("v2" in read(DESIGN_REL), "基线版本不得在矛盾未解决时递增")


def test_after_write_check_failure_does_not_complete_handoff() -> None:
    """保存后检查失败时保留已写入事实,不得宣布交接完成。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        read, meta, channel = _handoff_fixture(project, svc)
        sections = _sections()
        sections["purpose"] = {
            "content": "让玩家每天用一次短局回到游戏;依据见 "
                       "docs/missing-source.md。",
            "sources": ["Q1", "Q3"]}
        plan = plan_handoff({RECORD_REL: read(RECORD_REL)},
                            {**meta, "sections": sections},
                            _existing(project))
        check(plan["status"] == "planned",
              f"引用缺口在写入后检查,计划仍可整理,实际 {plan.get('status')}")
        session = begin({
            "mode": "new_design", "stage": "只有设计，尚未实现",
            "goal": "完成每日挑战核心模块", "module": "每日挑战",
            "deps": [], "entry": DESIGN_REL,
            "authorization": {"write": True, "sync": True},
            "baseline": {DESIGN_REL: sha256_text(read(DESIGN_REL))},
        })["session"]
        applied = apply_handoff(plan, channel, read, session=session)
        check(applied.get("written"),
              f"已写入事实须保留,实际 {applied.get('written')}")
        check(applied["saved"] is not True
              and applied["status"] == "check_failed",
              f"检查失败不得标已保存或交接完成,实际 {applied}")
        check(applied.get("next_round_ready") is not True,
              "检查失败后不得宣称下一轮可继续交接")
        check(applied.get("checks") and applied["checks"]["ok"] is False,
              f"须暴露 checks.ok=false,实际 {applied.get('checks')}")
        failures = "；".join(applied["checks"].get("failures") or [])
        check("新改引用不可定位:docs/missing-source.md" in failures,
              f"失败原因须可定位,实际 {failures}")
        check("已交接" not in applied["report"]
              or "检查失败" in applied["report"]
              or "未完成" in applied["report"],
              f"报告不得把检查失败写成已交接完成,实际 {applied['report']}")
        check(applied.get("to_sync") not in ([], None)
              or applied.get("states", {}).get("synced") is not True,
              "检查失败时不得把待同步清成无")
        restored = restore_from_records({RECORD_REL: read(RECORD_REL)}, "每日挑战")
        check(restored.get("baseline_synced") is not True,
              f"检查失败后恢复不得把基线标成已同步,实际 {restored}")
        check(restored.get("to_sync"),
              f"未完成同步须留在可恢复记录中,实际 {restored.get('to_sync')}")
        check("同步状态：待同步" in (read(RECORD_REL) or ""),
              "检查失败不得把决定记录写成已同步")


def _ascii_fingerprint_baseline() -> str:
    """有效 v2 基线:使用统一接口认可的英文冒号指纹登记。"""

    zeros = "0" * 64
    body = (
        "# 齿轮谜城：当前游戏需求与设计\n\n"
        "维护责任：方案设计。基线版本：v2。适用范围：全游戏。\n\n"
        "## 章节模式\n\n"
        "- 章节按关卡顺序解锁。\n\n"
        f"内容指纹:sha256:{zeros}\n"
        f"归一指纹:sha256:{zeros}\n")
    records_dir = PLUGIN_ROOT / "records"
    if str(records_dir) not in sys.path:
        sys.path.insert(0, str(records_dir))
    import mgs_records  # noqa: PLC0415

    strict = mgs_records._canonical_fingerprint(body)
    norm = mgs_records._normalized_fingerprint(body)
    return body.replace(f"内容指纹:sha256:{zeros}",
                        f"内容指纹:sha256:{strict}").replace(
        f"归一指纹:sha256:{zeros}", f"归一指纹:sha256:{norm}")


def test_english_colon_fingerprints_stay_consistent_after_sync() -> None:
    """已有英文冒号指纹须被兼容更新,正式统一检查不得变成实质变更。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        (project / DESIGN_REL).write_text(_ascii_fingerprint_baseline(),
                                          encoding="utf-8")
        before = _design_entry(_baseline_check(project))
        check(before["status"] == "一致",
              f"夹具须先登记为一致,实际 {before}")
        read, meta, channel = _handoff_fixture(project, svc)
        plan = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                            _existing(project))
        check(plan["status"] == "planned",
              f"可交接模块应进入计划,实际 {plan.get('status')}:{plan.get('gaps')}")
        applied = apply_handoff(plan, channel, read)
        check(applied["status"] == "saved", f"获准交接应落盘,实际 {applied}")
        design = read(DESIGN_REL)
        check(len(re.findall(r"内容指纹\s*[:：]\s*sha256:", design)) == 1,
              f"同步后只能保留一处内容指纹,实际 {design}")
        check(len(re.findall(r"归一指纹\s*[:：]\s*sha256:", design)) == 1,
              f"同步后只能保留一处归一指纹,实际 {design}")
        entry = _design_entry(_baseline_check(project))
        check(entry["status"] == "一致",
              f"正式统一检查须保持一致,实际 {entry}")
        verdict = verify_handoff(plan, {
            SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
            GLOSSARY_REL: read(GLOSSARY_REL), RECORD_REL: read(RECORD_REL)})
        check(verdict["ok"], f"接缝回读仍应通过,实际 {verdict}")


def test_partial_spec_write_replans_remaining_baseline_sync() -> None:
    """规格已写入但基线因版本冲突未同步时,重新规划不得跳过核心基线。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        read, meta, channel = _handoff_fixture(project, svc)
        first = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                             _existing(project))
        check(first["status"] == "planned",
              f"首次交接应可规划,实际 {first.get('status')}:{first.get('gaps')}")
        check(any(item.get("path") == DESIGN_REL for item in first["files"]),
              f"首次实质变化须包含核心基线,实际 {first['files']}")

        class _ConflictAfterSpec(_Channel):
            def write(self, path, content, expected_sha256=None, note=None):
                result = super().write(path, content,
                                       expected_sha256=expected_sha256,
                                       note=note)
                if path == SPEC_REL:
                    current = read(DESIGN_REL)
                    (project / DESIGN_REL).write_text(
                        current.rstrip() + "\n\n外部并发修改。\n",
                        encoding="utf-8")
                return result

        conflicted = apply_handoff(
            first, _ConflictAfterSpec(svc, channel.token), read)
        check(conflicted.get("status") == "conflict",
              f"基线被外部改动后须报版本冲突,实际 {conflicted}")
        check(SPEC_REL in (conflicted.get("written") or []),
              f"已写入的规格须保留,实际 {conflicted.get('written')}")
        check(SPEC_REL not in (read(DESIGN_REL) or ""),
              "冲突后核心基线不得假装已引用规格")

        retry = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                             _existing(project))
        check(retry["status"] == "planned",
              f"按实际文件重新规划应继续,实际 {retry.get('status')}")
        check(retry["version"]["change"] == "substantive",
              f"基线尚未引用规格时不得改判为格式修正,实际 {retry['version']}")
        check(any(item.get("path") == DESIGN_REL for item in retry["files"]),
              f"重新规划必须仍包含核心基线,实际 {retry['files']}")

        applied = apply_handoff(retry, channel, read)
        check(applied.get("saved") is True,
              f"冲突解除后应能完成剩余同步,实际 {applied}")
        design = read(DESIGN_REL)
        check(SPEC_REL in (design or ""),
              f"完成同步后基线必须引用模块规格,实际 {design}")
        check(applied.get("states", {}).get("synced") is True,
              f"基线引用就位后才可标已同步,实际 {applied.get('states')}")
        check(applied.get("to_sync") in ([], None),
              f"完成同步后待同步应清空,实际 {applied.get('to_sync')}")
        verdict = verify_handoff(retry, {
            SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
            GLOSSARY_REL: read(GLOSSARY_REL), RECORD_REL: read(RECORD_REL)})
        check(verdict["ok"], f"基线引用就位后回读应通过,实际 {verdict}")


def test_stale_baseline_citation_recovery_keeps_substantive() -> None:
    """基线仍指旧版本时,冲突恢复不得把实质变更降为格式修正。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        read = _reader(project)
        _seed_glossary(project)
        _save_record(save_channel, read,
                     (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),),
                     sync_qids=("Q1", "Q2"), owner=save_owner)
        meta = _meta(pending_impacts={"Q3": "等待补充;", "Q4": "影响存档结构;"},
                     blocking_qids=[])
        channel = _Channel(svc, _handoff_token(svc))
        first = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                             _existing(project))
        applied_first = apply_handoff(first, channel, read)
        check(applied_first["status"] == "saved"
              and applied_first.get("states", {}).get("synced") is True,
              f"首次交接应完成同步,实际 {applied_first}")
        check("当前 v3" in (read(DESIGN_REL) or ""),
              "夹具须先让基线引用指向 v3")

        # 修改已采纳决定:第 2 轮改 Q1,规格内容随之变化,计划 v3→v4。
        owner2 = _instance(svc)
        save2 = _Channel(svc, owner2.token)
        revised = run_round(_turn("Q1 调整为 从现有 20 关按日期抽取",
                                  round_no=2,
                                  settled={"Q1": "B 每日生成新关",
                                           "Q2": "B 与章节并存"},
                                  shown=["Q4"]))
        applied_revision = apply_save(
            plan_save(read(RECORD_REL), revised,
                      _record_meta(round_no=2,
                                   reply="Q1 调整为 从现有 20 关按日期抽取")),
            save2, read)
        check(applied_revision["status"] == "saved",
              f"修改决定应先经真实通道保存,实际 {applied_revision['status']}")
        save2.svc.release_instance(owner2.instance_id)
        save2.svc.reclaim_locks(owner2.instance_id)

        sections_v4 = _sections()
        sections_v4["rules"] = {
            "content": "按 Q1 修订:选择本机日期对应关卡(从现有 20 关按日期"
                       "抽取) → 完成一局 → 按步数结算 → 更新当日最佳;每日只"
                       "保留一个最佳值。",
            "sources": ["Q1", "Q4"]}
        meta_v4 = _meta(sections=sections_v4,
                        pending_impacts={"Q3": "等待补充;",
                                         "Q4": "影响存档结构;"},
                        blocking_qids=[], version_from="v3", version_to="v4",
                        sync_ref="GAME_DESIGN v4 / spec-每日挑战 v2")

        class _ConflictAfterSpec(_Channel):
            def write(self, path, content, expected_sha256=None, note=None):
                result = super().write(path, content,
                                       expected_sha256=expected_sha256,
                                       note=note)
                if path == SPEC_REL:
                    current = read(DESIGN_REL)
                    (project / DESIGN_REL).write_text(
                        current.rstrip() + "\n\n外部并发修改。\n",
                        encoding="utf-8")
                return result

        second = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta_v4,
                              _existing(project))
        check(second["version"]["change"] == "substantive"
              and second["version"]["to"] == "v4",
              f"修改决定的交接应计划 v3→v4,实际 {second['version']}")
        conflicted = apply_handoff(second, _ConflictAfterSpec(svc,
                                                              channel.token),
                                   read)
        check(conflicted.get("status") == "conflict",
              f"基线被外部改动后须报版本冲突,实际 {conflicted}")
        check(SPEC_REL in (conflicted.get("written") or []),
              "已写入的规格须保留")

        # 按实际文件重新读取规划:旧 v3 引用不得当成新修订已同步。
        retry = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta_v4,
                             _existing(project))
        check(retry["status"] == "planned",
              f"重新规划应继续,实际 {retry.get('status')}")
        check(retry["compare"]["semantic_equal"] is True,
              "磁盘规格已含新决定,回读语义一致(易误判为格式修正的路径)")
        check(retry["version"]["change"] == "substantive"
              and retry["version"]["from"] == "v3"
              and retry["version"]["to"] == "v4",
              f"基线仍指 v3 时不得降为格式修正 v3→v3,实际 {retry['version']}")
        check(any(item.get("path") == DESIGN_REL for item in retry["files"]),
              f"重新规划必须仍包含核心基线,实际 {retry['files']}")
        restored = restore_from_records({RECORD_REL: read(RECORD_REL)},
                                        "每日挑战")
        check(restored.get("to_sync") == ["Q1"],
              f"未完成同步的决定须保持可定位,实际 {restored.get('to_sync')}")

        applied_retry = apply_handoff(retry, channel, read)
        check(applied_retry.get("saved") is True,
              f"冲突解除后应完成剩余同步,实际 {applied_retry}")
        design = read(DESIGN_REL) or ""
        check("当前 v4" in design,
              f"基线引用须更新到当前版本 v4,实际 {design}")
        check(applied_retry.get("states", {}).get("synced") is True,
              f"基线引用就位后才可标已同步,实际 {applied_retry.get('states')}")
        check(applied_retry.get("to_sync") in ([], None),
              f"完成同步后待同步应清空,实际 {applied_retry.get('to_sync')}")
        verdict = verify_handoff(retry, {
            SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
            GLOSSARY_REL: read(GLOSSARY_REL), RECORD_REL: read(RECORD_REL)})
        check(verdict["ok"], f"基线引用就位后回读应通过,实际 {verdict}")


def test_custom_titled_citation_updates_on_recovery() -> None:
    """自定义标题的引用节在冲突恢复时也须更新,不得丢失待同步事实。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        read = _reader(project)
        _seed_glossary(project)
        _save_record(save_channel, read,
                     (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),),
                     sync_qids=("Q1", "Q2"), owner=save_owner)
        meta = _meta(pending_impacts={"Q3": "等待补充;", "Q4": "影响存档结构;"},
                     blocking_qids=[])
        channel = _Channel(svc, _handoff_token(svc))
        first = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                             _existing(project))
        applied_first = apply_handoff(first, channel, read)
        check(applied_first["status"] == "saved"
              and applied_first.get("states", {}).get("synced") is True,
              f"首次交接应完成同步,实际 {applied_first}")
        design_after_first = read(DESIGN_REL) or ""
        check("当前 v3" in design_after_first,
              "夹具须先让基线引用指向 v3")
        # 外部把标准引用标题改为自定义标题:内容仍指旧 v3。
        (project / DESIGN_REL).write_text(
            design_after_first.replace("## 每日挑战模块规格引用",
                                       "## 每日挑战设计依据"),
            encoding="utf-8")

        owner2 = _instance(svc)
        save2 = _Channel(svc, owner2.token)
        revised = run_round(_turn("Q1 调整为 从现有 20 关按日期抽取",
                                  round_no=2,
                                  settled={"Q1": "B 每日生成新关",
                                           "Q2": "B 与章节并存"},
                                  shown=["Q4"]))
        applied_revision = apply_save(
            plan_save(read(RECORD_REL), revised,
                      _record_meta(round_no=2,
                                   reply="Q1 调整为 从现有 20 关按日期抽取")),
            save2, read)
        check(applied_revision["status"] == "saved",
              f"修改决定应先经真实通道保存,实际 {applied_revision['status']}")
        save2.svc.release_instance(owner2.instance_id)
        save2.svc.reclaim_locks(owner2.instance_id)

        sections_v4 = _sections()
        sections_v4["rules"] = {
            "content": "按 Q1 修订:选择本机日期对应关卡(从现有 20 关按日期"
                       "抽取) → 完成一局 → 按步数结算 → 更新当日最佳;每日只"
                       "保留一个最佳值。",
            "sources": ["Q1", "Q4"]}
        meta_v4 = _meta(sections=sections_v4,
                        pending_impacts={"Q3": "等待补充;",
                                         "Q4": "影响存档结构;"},
                        blocking_qids=[], version_from="v3", version_to="v4",
                        sync_ref="GAME_DESIGN v4 / spec-每日挑战 v2")

        class _ConflictAfterSpec(_Channel):
            def write(self, path, content, expected_sha256=None, note=None):
                result = super().write(path, content,
                                       expected_sha256=expected_sha256,
                                       note=note)
                if path == SPEC_REL:
                    current = read(DESIGN_REL)
                    (project / DESIGN_REL).write_text(
                        current.rstrip() + "\n\n外部并发修改。\n",
                        encoding="utf-8")
                return result

        second = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta_v4,
                              _existing(project))
        conflicted = apply_handoff(second, _ConflictAfterSpec(svc,
                                                              channel.token),
                                   read)
        check(conflicted.get("status") == "conflict",
              f"基线被外部改动后须报版本冲突,实际 {conflicted}")

        retry = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta_v4,
                             _existing(project))
        check(retry["version"]["change"] == "substantive"
              and retry["version"]["to"] == "v4",
              f"旧 v3 引用不得当成新修订已同步,实际 {retry['version']}")
        applied_retry = apply_handoff(retry, channel, read)
        check(applied_retry.get("saved") is True,
              f"重试应完成剩余同步,实际 {applied_retry}")
        design = read(DESIGN_REL) or ""
        check("当前 v4" in design,
              f"自定义标题的引用节也须更新到当前版本,实际 {design}")
        check(applied_retry.get("states", {}).get("synced") is True,
              f"引用真正就位后才可标已同步,实际 {applied_retry.get('states')}")
        check(applied_retry.get("to_sync") in ([], None),
              f"决定记录与基线引用须一致收口,实际 {applied_retry.get('to_sync')}")
        state = restore_from_records({RECORD_REL: read(RECORD_REL)},
                                     "每日挑战")
        check(state["to_sync"] == [],
              f"恢复不得留下已同步却仍待同步的矛盾,实际 {state['to_sync']}")
        check(state["baseline_synced"] is True,
              "恢复时基线引用已就位,不得把已同步降回待同步")
        verdict = verify_handoff(retry, {
            SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
            GLOSSARY_REL: read(GLOSSARY_REL), RECORD_REL: read(RECORD_REL)})
        check(verdict["ok"], f"自定义标题恢复后回读应通过,实际 {verdict}")


def test_custom_section_mixed_content_preserved() -> None:
    """自定义节混有未受影响规则时,更新引用不得删掉同节其他要求。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        save_owner = _instance(svc)
        save_channel = _Channel(svc, save_owner.token)
        read = _reader(project)
        _seed_glossary(project)
        _save_record(save_channel, read,
                     (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),),
                     sync_qids=("Q1", "Q2"), owner=save_owner)
        meta = _meta(pending_impacts={"Q3": "等待补充;", "Q4": "影响存档结构;"},
                     blocking_qids=[])
        channel = _Channel(svc, _handoff_token(svc))
        first = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                             _existing(project))
        applied_first = apply_handoff(first, channel, read)
        check(applied_first["status"] == "saved"
              and applied_first.get("states", {}).get("synced") is True,
              f"首次交接应完成同步,实际 {applied_first}")
        design_after_first = read(DESIGN_REL) or ""
        check("当前 v3" in design_after_first,
              "夹具须先让基线引用指向 v3")
        # 外部把引用节改为自定义标题,并混入一条与本次修改无关的有效规则。
        (project / DESIGN_REL).write_text(
            design_after_first
            .replace("## 每日挑战模块规格引用", "## 系统设计依据")
            .replace("- 技术约定：引用技术设计,不代写。\n",
                     "- 技术约定：引用技术设计,不代写。\n"
                     "- 主线第 10 关通过后解锁章节选择。\n"),
            encoding="utf-8")

        owner2 = _instance(svc)
        save2 = _Channel(svc, owner2.token)
        revised = run_round(_turn("Q1 调整为 从现有 20 关按日期抽取",
                                  round_no=2,
                                  settled={"Q1": "B 每日生成新关",
                                           "Q2": "B 与章节并存"},
                                  shown=["Q4"]))
        applied_revision = apply_save(
            plan_save(read(RECORD_REL), revised,
                      _record_meta(round_no=2,
                                   reply="Q1 调整为 从现有 20 关按日期抽取")),
            save2, read)
        check(applied_revision["status"] == "saved",
              f"修改决定应先经真实通道保存,实际 {applied_revision['status']}")
        save2.svc.release_instance(owner2.instance_id)
        save2.svc.reclaim_locks(owner2.instance_id)

        sections_v4 = _sections()
        sections_v4["rules"] = {
            "content": "按 Q1 修订:选择本机日期对应关卡(从现有 20 关按日期"
                       "抽取) → 完成一局 → 按步数结算 → 更新当日最佳;每日只"
                       "保留一个最佳值。",
            "sources": ["Q1", "Q4"]}
        meta_v4 = _meta(sections=sections_v4,
                        pending_impacts={"Q3": "等待补充;",
                                         "Q4": "影响存档结构;"},
                        blocking_qids=[], version_from="v3", version_to="v4",
                        sync_ref="GAME_DESIGN v4 / spec-每日挑战 v2")

        class _ConflictAfterSpec(_Channel):
            def write(self, path, content, expected_sha256=None, note=None):
                result = super().write(path, content,
                                       expected_sha256=expected_sha256,
                                       note=note)
                if path == SPEC_REL:
                    current = read(DESIGN_REL)
                    (project / DESIGN_REL).write_text(
                        current.rstrip() + "\n\n外部并发修改。\n",
                        encoding="utf-8")
                return result

        second = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta_v4,
                              _existing(project))
        conflicted = apply_handoff(second, _ConflictAfterSpec(svc,
                                                              channel.token),
                                   read)
        check(conflicted.get("status") == "conflict",
              f"基线被外部改动后须报版本冲突,实际 {conflicted}")

        retry = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta_v4,
                             _existing(project))
        applied_retry = apply_handoff(retry, channel, read)
        check(applied_retry.get("saved") is True,
              f"重试应完成剩余同步,实际 {applied_retry}")
        design = read(DESIGN_REL) or ""
        check("当前 v4" in design,
              f"混合节中的目标引用须更新到当前版本,实际 {design}")
        check("主线第 10 关通过后解锁章节选择" in design,
              f"同节未受影响的规则不得被删除,实际 {design}")
        check(applied_retry.get("states", {}).get("synced") is True
              and applied_retry.get("to_sync") in ([], None),
              f"同步状态须一致收口,实际 {applied_retry.get('states')}")
        verdict = verify_handoff(retry, {
            SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
            GLOSSARY_REL: read(GLOSSARY_REL), RECORD_REL: read(RECORD_REL)})
        check(verdict["ok"], f"混合节保留后回读应通过,实际 {verdict}")


def _recover_stale_custom_citation(tmp: str, mutate):
    """首次交接后按 mutate 改写基线,再走 v3→v4 冲突恢复。"""

    svc, project = _service(Path(tmp))
    save_owner = _instance(svc)
    save_channel = _Channel(svc, save_owner.token)
    read = _reader(project)
    _seed_glossary(project)
    _save_record(save_channel, read,
                 (("Q1 选 B, Q2 选 B", ["Q1", "Q2", "Q3"]),),
                 sync_qids=("Q1", "Q2"), owner=save_owner)
    meta = _meta(pending_impacts={"Q3": "等待补充;", "Q4": "影响存档结构;"},
                 blocking_qids=[])
    channel = _Channel(svc, _handoff_token(svc))
    first = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta,
                         _existing(project))
    applied_first = apply_handoff(first, channel, read)
    check(applied_first["status"] == "saved"
          and applied_first.get("states", {}).get("synced") is True,
          f"首次交接应完成同步,实际 {applied_first}")
    design_after_first = read(DESIGN_REL) or ""
    check("当前 v3" in design_after_first, "夹具须先让基线引用指向 v3")
    (project / DESIGN_REL).write_text(mutate(design_after_first),
                                      encoding="utf-8")

    owner2 = _instance(svc)
    save2 = _Channel(svc, owner2.token)
    revised = run_round(_turn("Q1 调整为 从现有 20 关按日期抽取",
                              round_no=2,
                              settled={"Q1": "B 每日生成新关",
                                       "Q2": "B 与章节并存"},
                              shown=["Q4"]))
    applied_revision = apply_save(
        plan_save(read(RECORD_REL), revised,
                  _record_meta(round_no=2,
                               reply="Q1 调整为 从现有 20 关按日期抽取")),
        save2, read)
    check(applied_revision["status"] == "saved",
          f"修改决定应先经真实通道保存,实际 {applied_revision['status']}")
    save2.svc.release_instance(owner2.instance_id)
    save2.svc.reclaim_locks(owner2.instance_id)

    sections_v4 = _sections()
    sections_v4["rules"] = {
        "content": "按 Q1 修订:选择本机日期对应关卡(从现有 20 关按日期"
                   "抽取) → 完成一局 → 按步数结算 → 更新当日最佳;每日只"
                   "保留一个最佳值。",
        "sources": ["Q1", "Q4"]}
    meta_v4 = _meta(sections=sections_v4,
                    pending_impacts={"Q3": "等待补充;",
                                     "Q4": "影响存档结构;"},
                    blocking_qids=[], version_from="v3", version_to="v4",
                    sync_ref="GAME_DESIGN v4 / spec-每日挑战 v2")

    class _ConflictAfterSpec(_Channel):
        def write(self, path, content, expected_sha256=None, note=None):
            result = super().write(path, content,
                                   expected_sha256=expected_sha256,
                                   note=note)
            if path == SPEC_REL:
                current = read(DESIGN_REL)
                (project / DESIGN_REL).write_text(
                    current.rstrip() + "\n\n外部并发修改。\n",
                    encoding="utf-8")
            return result

    second = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta_v4,
                          _existing(project))
    conflicted = apply_handoff(second, _ConflictAfterSpec(svc, channel.token),
                               read)
    check(conflicted.get("status") == "conflict",
          f"基线被外部改动后须报版本冲突,实际 {conflicted}")
    retry = plan_handoff({RECORD_REL: read(RECORD_REL)}, meta_v4,
                         _existing(project))
    applied = apply_handoff(retry, channel, read)
    return applied, read(DESIGN_REL) or "", retry, read


def _same_line_list_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = (f"- 每日挑战详见 {SPEC_REL}（当前 v2）；"
           "主线第 10 关通过后解锁章节选择。")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _same_line_table_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"| 规格 | 规则 |\n| --- | --- |\n"
           f"| {SPEC_REL}（当前 v2） | "
           "主线第 10 关通过后解锁章节选择 |\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _duplicate_citation_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 每日挑战详见 {SPEC_REL}（当前 v2）。\n"
           f"- 第二条引用说明：{SPEC_REL}（当前 v2）也用于说明"
           "主线第 10 关通过后解锁章节选择。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def test_same_line_citation_layouts_keep_rules() -> None:
    """审查独立输入:同行列表、表格与第二条重复引用说明。"""

    cases = (
        ("list", _same_line_list_layout,
         f"- 每日挑战详见 {SPEC_REL}（当前 v4）；"
         "主线第 10 关通过后解锁章节选择。"),
        ("table", _same_line_table_layout,
         f"| {SPEC_REL}（当前 v4） | 主线第 10 关通过后解锁章节选择 |"),
        ("duplicate", _duplicate_citation_layout, None),
    )
    for name, mutate, expected in cases:
        with tempfile.TemporaryDirectory() as tmp:
            applied, design, retry, read = _recover_stale_custom_citation(
                tmp, mutate)
            check(applied.get("saved") is True,
                  f"{name}: 重试应完成剩余同步,实际 {applied}")
            check("当前 v4" in design,
                  f"{name}: 目标引用须更新到当前版本,实际 {design}")
            check("主线第 10 关通过后解锁章节选择" in design,
                  f"{name}: 同行未撤销的规则不得被删除,实际 {design}")
            if expected:
                check(expected in design,
                      f"{name}: 须只更新引用版本并保留同行结构,实际 {design}")
            else:
                check("第二条引用说明" in design,
                      f"{name}: 重复引用行的说明不得整行删除,实际 {design}")
            check(applied.get("states", {}).get("synced") is True
                  and applied.get("to_sync") in ([], None),
                  f"{name}: 同步状态须一致收口,实际 {applied}")
            verdict = verify_handoff(retry, {
                SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
                GLOSSARY_REL: read(GLOSSARY_REL),
                RECORD_REL: read(RECORD_REL)})
            check(verdict["ok"], f"{name}: 保留规则后回读应通过,实际 {verdict}")


def _link_citation_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 每日挑战入口：[每日挑战]({SPEC_REL}) 优先复用既有内容。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _other_module_version_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = (f"- 每日规则：{SPEC_REL}；章节系统（当前 v7）规则："
           "每日关不与章节进度冲突。")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _neighbor_table_version_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"| 规格 | 关联 |\n| --- | --- |\n"
           f"| {SPEC_REL} | docs/mygamestudio/records/spec-章节.md"
           "（当前 v8） | 每日规则 |\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _bracket_rules_duplicate_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 主引用：{SPEC_REL}（当前 v2）。\n"
           f"- 关联依据：{SPEC_REL}（当前 v2；章节十解锁跳关功能）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def test_reference_boundary_keeps_links_other_modules_and_rules() -> None:
    """引用边界:版本不进链接目标,不改其他模块版本,不吞括号内规则。"""

    cases = (
        ("link", _link_citation_layout,
         [f"[每日挑战]({SPEC_REL})（当前 v4）"],
         [f"]({SPEC_REL}（当前"]),
        ("other-module", _other_module_version_layout,
         [f"- 每日规则：{SPEC_REL}（当前 v4）；章节系统（当前 v7）规则："
          "每日关不与章节进度冲突。"],
         ["章节系统（当前 v4）"]),
        ("neighbor-table", _neighbor_table_version_layout,
         [f"| {SPEC_REL}（当前 v4） | docs/mygamestudio/records/spec-章节.md"
          "（当前 v8） | 每日规则 |"],
         ["spec-章节.md（当前 v4）"]),
        ("bracket-rules", _bracket_rules_duplicate_layout,
         ["- 关联依据：（章节十解锁跳关功能）。"],
         ["（当前 v2；章节十解锁跳关功能）"]),
    )
    for name, mutate, expected, forbidden in cases:
        with tempfile.TemporaryDirectory() as tmp:
            applied, design, retry, read = _recover_stale_custom_citation(
                tmp, mutate)
            check(applied.get("saved") is True,
                  f"{name}: 重试应完成剩余同步,实际 {applied}")
            for needle in expected:
                check(needle in design,
                      f"{name}: 须精确更新本引用并保留其余内容,期望含 "
                      f"{needle!r},实际 {design}")
            for needle in forbidden:
                check(needle not in design,
                      f"{name}: 不得出现越界改动 {needle!r},实际 {design}")
            check(applied.get("states", {}).get("synced") is True
                  and applied.get("to_sync") in ([], None),
                  f"{name}: 同步状态须一致收口,实际 {applied}")
            verdict = verify_handoff(retry, {
                SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
                GLOSSARY_REL: read(GLOSSARY_REL),
                RECORD_REL: read(RECORD_REL)})
            check(verdict["ok"], f"{name}: 边界保留后回读应通过,实际 {verdict}")


def _angled_link_citation_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = (f"- 每日挑战入口：[挑战说明](<{SPEC_REL}>)"
           " 优先复用既有内容。")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _link_with_version_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = (f"- 每日挑战入口：[每日挑战]({SPEC_REL})"
           "（当前 v3；仍需离线可用）。")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _longer_filename_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 主引用：{SPEC_REL}.backup（当前 v9）。\n"
           f"- 目标引用：{SPEC_REL}（当前 v3）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _nested_bracket_update_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 主引用：{SPEC_REL}（参照章节模块（当前 v8）的解锁规则）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _nested_bracket_strip_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 主引用：{SPEC_REL}（当前 v2）。\n"
           f"- 参加条件：{SPEC_REL}（章节模式（当前 v8）开启后才能参加"
           "每日挑战）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def test_citation_identity_keeps_link_targets_longer_names_and_nested_versions() -> None:
    """引用身份:尖括号链接目标、链接后已有版本、更长文件名与嵌套版本。"""

    cases = (
        ("angled-link", _angled_link_citation_layout,
         [f"[挑战说明](<{SPEC_REL}>)（当前 v4）"],
         [f"](<{SPEC_REL}（当前"]),
        ("link-with-version", _link_with_version_layout,
         [f"[每日挑战]({SPEC_REL})（当前 v4；仍需离线可用）"],
         ["（当前 v4）（当前 v3"]),
        ("longer-filename", _longer_filename_layout,
         [f"{SPEC_REL}.backup（当前 v9）",
          f"目标引用：{SPEC_REL}（当前 v4）"],
         ["（当前 v4）.backup", "目标引用：。"]),
        ("nested-update", _nested_bracket_update_layout,
         [f"主引用：{SPEC_REL}"
          "（当前 v4；参照章节模块（当前 v8）的解锁规则）"],
         ["章节模块（当前 v4）"]),
        ("nested-strip", _nested_bracket_strip_layout,
         ["参加条件：（章节模式（当前 v8）开启后才能参加每日挑战）。"],
         ["章节模式（）"]),
    )
    for name, mutate, expected, forbidden in cases:
        with tempfile.TemporaryDirectory() as tmp:
            applied, design, retry, read = _recover_stale_custom_citation(
                tmp, mutate)
            check(applied.get("saved") is True,
                  f"{name}: 重试应完成剩余同步,实际 {applied}")
            for needle in expected:
                check(needle in design,
                      f"{name}: 须按完整引用身份原位更新,期望含 "
                      f"{needle!r},实际 {design}")
            for needle in forbidden:
                check(needle not in design,
                      f"{name}: 不得出现越界改动 {needle!r},实际 {design}")
            check(applied.get("states", {}).get("synced") is True
                  and applied.get("to_sync") in ([], None),
                  f"{name}: 同步状态须一致收口,实际 {applied}")
            verdict = verify_handoff(retry, {
                SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
                GLOSSARY_REL: read(GLOSSARY_REL),
                RECORD_REL: read(RECORD_REL)})
            check(verdict["ok"], f"{name}: 身份保留后回读应通过,实际 {verdict}")


def _spaced_link_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = (f"- 每日挑战入口：[挑战说明]( {SPEC_REL} )"
           "（当前 v3；规则）。")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _spaced_angled_link_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = (f"- 每日挑战入口：[挑战说明]( <{SPEC_REL}> )"
           " 优先复用既有内容。")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _titled_link_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = (f"- 每日挑战规则：[规则]({SPEC_REL} \"每日挑战(离线)\")"
           "（当前 v3）。")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _tilde_backup_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 主引用：{SPEC_REL}~（当前 v9）。\n"
           f"- 目标引用：{SPEC_REL}（当前 v3）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _dot_slash_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 主引用：./{SPEC_REL}（当前 v3）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _cjk_adjacent_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 主引用：详见{SPEC_REL}（当前 v3）的规则。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _self_link_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 主引用：[{SPEC_REL}]({SPEC_REL})（当前 v3）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _mid_text_version_update_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 主引用：{SPEC_REL}（参照章节模块当前 v8 的规则）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _mid_text_version_strip_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 主引用：{SPEC_REL}（当前 v2）。\n"
           f"- 参照说明：{SPEC_REL}（参照章节模块当前 v8 的规则）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def test_link_target_parsing_and_version_ownership_keep_valid_citations() -> None:
    """链接目标完整解析与版本归属:空白目标、标题、备份文件、紧邻引用。"""

    cases = (
        ("spaced-link", _spaced_link_layout,
         [f"[挑战说明]( {SPEC_REL} )（当前 v4；规则）"],
         [f"]( {SPEC_REL}（当前", "（当前 v4）（当前 v3"]),
        ("spaced-angled", _spaced_angled_link_layout,
         [f"[挑战说明]( <{SPEC_REL}> )（当前 v4）"],
         [f"<{SPEC_REL}（当前"]),
        ("titled-link", _titled_link_layout,
         [f"[规则]({SPEC_REL} \"每日挑战(离线)\")（当前 v4）"],
         ["每日挑战(离线（当前", "（当前 v4）（当前 v3"]),
        ("tilde-backup", _tilde_backup_layout,
         [f"{SPEC_REL}~（当前 v9）",
          f"目标引用：{SPEC_REL}（当前 v4）"],
         ["（当前 v4）~", "目标引用：。"]),
        ("dot-slash", _dot_slash_layout,
         [f"./{SPEC_REL}（当前 v4）"], []),
        ("cjk-adjacent", _cjk_adjacent_layout,
         [f"详见{SPEC_REL}（当前 v4）的规则"], []),
        ("self-link", _self_link_layout,
         [f"[{SPEC_REL}]({SPEC_REL})（当前 v4）"],
         [f"（当前 v4）]({SPEC_REL})", "（当前 v4）（当前 v3"]),
        ("mid-text-update", _mid_text_version_update_layout,
         [f"主引用：{SPEC_REL}（当前 v4；参照章节模块当前 v8 的规则）"],
         ["章节模块当前 v4"]),
        ("mid-text-strip", _mid_text_version_strip_layout,
         ["参照说明：（参照章节模块当前 v8 的规则）。"],
         ["章节模块；的规则", "章节模块当前 v4"]),
    )
    for name, mutate, expected, forbidden in cases:
        with tempfile.TemporaryDirectory() as tmp:
            applied, design, retry, read = _recover_stale_custom_citation(
                tmp, mutate)
            check(applied.get("saved") is True,
                  f"{name}: 重试应完成剩余同步,实际 {applied}")
            for needle in expected:
                check(needle in design,
                      f"{name}: 须按引用语法原位更新,期望含 "
                      f"{needle!r},实际 {design}")
            for needle in forbidden:
                check(needle not in design,
                      f"{name}: 不得出现越界改动 {needle!r},实际 {design}")
            check(applied.get("states", {}).get("synced") is True
                  and applied.get("to_sync") in ([], None),
                  f"{name}: 同步状态须一致收口,实际 {applied}")
            verdict = verify_handoff(retry, {
                SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
                GLOSSARY_REL: read(GLOSSARY_REL),
                RECORD_REL: read(RECORD_REL)})
            check(verdict["ok"], f"{name}: 引用保留后回读应通过,实际 {verdict}")


def _archive_path_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 历史规格：archive/{SPEC_REL}（当前 v8；旧版题库）。\n"
           f"- 当前规格：{SPEC_REL}（当前 v3）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _paren_file_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 历史规格：{SPEC_REL}(backup)（当前 v9）。\n"
           f"- 当前规格：{SPEC_REL}（当前 v3）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _dot_slash_link_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 每日挑战入口：[每日挑战](./{SPEC_REL})（当前 v3）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _label_path_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 每日挑战入口：[查看 {SPEC_REL}]({SPEC_REL})（当前 v3）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _code_span_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 主引用：`{SPEC_REL}`（当前 v3）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _anchor_link_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 每日挑战入口：[正常流程]({SPEC_REL}#正常流程)（当前 v3）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def test_path_identity_and_markdown_boundaries_keep_other_files_and_targets() -> None:
    """完整路径 token 身份:归档目录、括号文件名、./链接、显示文字、代码片段。"""

    cases = (
        ("archive", _archive_path_layout,
         [f"archive/{SPEC_REL}（当前 v8；旧版题库）",
          f"当前规格：{SPEC_REL}（当前 v4）"],
         [f"archive/{SPEC_REL}（当前 v4", "当前规格：。"]),
        ("paren-file", _paren_file_layout,
         [f"{SPEC_REL}(backup)（当前 v9）",
          f"当前规格：{SPEC_REL}（当前 v4）"],
         [f"{SPEC_REL}(当前 v4", "当前规格：。"]),
        ("dot-slash-link", _dot_slash_link_layout,
         [f"[每日挑战](./{SPEC_REL})（当前 v4）"],
         [f"](./{SPEC_REL}（当前", "（当前 v4）（当前 v3"]),
        ("label-path", _label_path_layout,
         [f"[查看 {SPEC_REL}]({SPEC_REL})（当前 v4）"],
         [f"{SPEC_REL}（当前 v4）]({SPEC_REL})"]),
        ("code-span", _code_span_layout,
         [f"`{SPEC_REL}`（当前 v4）"],
         [f"`{SPEC_REL}（当前 v4）`"]),
        ("anchor-link", _anchor_link_layout,
         [f"[正常流程]({SPEC_REL}#正常流程)（当前 v4）"],
         [f"#正常流程（当前 v4"]),
    )
    for name, mutate, expected, forbidden in cases:
        with tempfile.TemporaryDirectory() as tmp:
            applied, design, retry, read = _recover_stale_custom_citation(
                tmp, mutate)
            check(applied.get("saved") is True,
                  f"{name}: 重试应完成剩余同步,实际 {applied}")
            for needle in expected:
                check(needle in design,
                      f"{name}: 须按完整 token 身份原位更新,期望含 "
                      f"{needle!r},实际 {design}")
            for needle in forbidden:
                check(needle not in design,
                      f"{name}: 不得出现越界改动 {needle!r},实际 {design}")
            check(applied.get("states", {}).get("synced") is True
                  and applied.get("to_sync") in ([], None),
                  f"{name}: 同步状态须一致收口,实际 {applied}")
            verdict = verify_handoff(retry, {
                SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
                GLOSSARY_REL: read(GLOSSARY_REL),
                RECORD_REL: read(RECORD_REL)})
            check(verdict["ok"], f"{name}: 身份保留后回读应通过,实际 {verdict}")


def _label_with_text_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 每日挑战入口：[{SPEC_REL} 规格说明]({SPEC_REL})（当前 v3）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _backup_target_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 历史规格：[历史规格](<{SPEC_REL}（备份）>)（当前 v8）。\n"
           f"- 当前：{SPEC_REL}（当前 v3）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _unicode_suffix_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 历史规格：[备份](<{SPEC_REL}副本>)（当前 v8）。\n"
           f"- 当前：{SPEC_REL}（当前 v3）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _linkdef_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 引用定义：[daily]: {SPEC_REL} \"标题\""
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _double_code_span_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 主引用：``{SPEC_REL}``（当前 v3）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def test_link_structure_identity_keeps_labels_targets_and_code_spans() -> None:
    """链接结构身份:显示文字、Unicode 目标后缀、引用式定义与双反引号。"""

    cases = (
        ("label-with-text", _label_with_text_layout,
         [f"[{SPEC_REL} 规格说明]({SPEC_REL})（当前 v4）"],
         [f"{SPEC_REL}（当前 v4） 规格说明"]),
        ("backup-target", _backup_target_layout,
         [f"[历史规格](<{SPEC_REL}（备份）>)（当前 v8）",
          f"- 当前：{SPEC_REL}（当前 v4）"],
         [f"<{SPEC_REL}（当前 v4", "当前：。"]),
        ("unicode-suffix", _unicode_suffix_layout,
         [f"[备份](<{SPEC_REL}副本>)（当前 v8）",
          f"- 当前：{SPEC_REL}（当前 v4）"],
         [f"<{SPEC_REL}（当前 v4", f"[当前 v4", "当前：。"]),
        ("double-code-span", _double_code_span_layout,
         [f"``{SPEC_REL}``（当前 v4）"],
         [f"``{SPEC_REL}（当前 v4）``"]),
    )
    for name, mutate, expected, forbidden in cases:
        with tempfile.TemporaryDirectory() as tmp:
            applied, design, retry, read = _recover_stale_custom_citation(
                tmp, mutate)
            check(applied.get("saved") is True,
                  f"{name}: 重试应完成剩余同步,实际 {applied}")
            for needle in expected:
                check(needle in design,
                      f"{name}: 须按完整链接结构原位更新,期望含 "
                      f"{needle!r},实际 {design}")
            for needle in forbidden:
                check(needle not in design,
                      f"{name}: 不得出现越界改动 {needle!r},实际 {design}")
            check(applied.get("states", {}).get("synced") is True
                  and applied.get("to_sync") in ([], None),
                  f"{name}: 同步状态须一致收口,实际 {applied}")
            verdict = verify_handoff(retry, {
                SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
                GLOSSARY_REL: read(GLOSSARY_REL),
                RECORD_REL: read(RECORD_REL)})
            check(verdict["ok"], f"{name}: 结构保留后回读应通过,实际 {verdict}")

    with tempfile.TemporaryDirectory() as tmp:
        applied, design, retry, read = _recover_stale_custom_citation(
            tmp, _linkdef_layout)
        check(f"[daily]: {SPEC_REL} \"标题\"" in design
              and f"[daily]: {SPEC_REL}（当前" not in design,
              f"linkdef: 引用式定义行必须原样保留,实际 {design}")
        check(not (applied.get("states", {}).get("synced") is True
                   and applied.get("to_sync") in ([], None)),
              f"linkdef: 无安全附着位置时不得宣称同步完成,实际 {applied}")
        verdict = verify_handoff(retry, {
            SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
            GLOSSARY_REL: read(GLOSSARY_REL),
            RECORD_REL: read(RECORD_REL)})
        check(not verdict["ok"],
              f"linkdef: 未完成的同步回读必须失败,实际 {verdict}")


def _multiline_link_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 每日挑战入口：[每日挑战](\n  {SPEC_REL}\n)（当前 v3）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _bare_cjk_suffix_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 历史规格：{SPEC_REL}副本（当前 v8）。\n"
           f"- 当前：{SPEC_REL}（当前 v3）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _backtick_cjk_copy_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 历史规格：`{SPEC_REL}副本`（当前 v8）。\n"
           f"- 当前：{SPEC_REL}（当前 v3）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _spaced_code_span_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。")
    new = f"- 主引用：` {SPEC_REL} `（当前 v3；保持离线）。"
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def _angled_dot_file_layout(text: str) -> str:
    old = (f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}"
           "（当前 v3；具体规则集中维护在那里,本文件只引用）。\n")
    new = (f"- 历史规格：[备份](<{SPEC_REL}.>)（当前 v8）。\n"
           f"- 当前：{SPEC_REL}（当前 v3）。\n")
    return text.replace("## 每日挑战模块规格引用", "## 系统设计依据").replace(
        old, new)


def test_round14_cross_line_links_complete_identity_and_code_spans() -> None:
    """r14:跨行链接保守不动、裸路径完整身份、带空格代码片段、目标尾点。"""

    cases = (
        ("bare-cjk-suffix", _bare_cjk_suffix_layout,
         [f"{SPEC_REL}副本（当前 v8）", f"- 当前：{SPEC_REL}（当前 v4）"],
         [f"{SPEC_REL}（当前 v4）副本", "当前：。"]),
        ("backtick-cjk-copy", _backtick_cjk_copy_layout,
         [f"`{SPEC_REL}副本`（当前 v8）", f"- 当前：{SPEC_REL}（当前 v4）"],
         [f"{SPEC_REL}（当前 v4）副本", "当前：。"]),
        ("spaced-code-span", _spaced_code_span_layout,
         [f"` {SPEC_REL} `（当前 v4；保持离线）"],
         [f"{SPEC_REL}（当前 v4）"]),
        ("angled-dot-file", _angled_dot_file_layout,
         [f"[备份](<{SPEC_REL}.>)（当前 v8）",
          f"- 当前：{SPEC_REL}（当前 v4）"],
         [f"[备份](<{SPEC_REL}.>)（当前 v4）", "当前：。"]),
    )
    for name, mutate, expected, forbidden in cases:
        with tempfile.TemporaryDirectory() as tmp:
            applied, design, retry, read = _recover_stale_custom_citation(
                tmp, mutate)
            check(applied.get("saved") is True,
                  f"{name}: 重试应完成剩余同步,实际 {applied}")
            for needle in expected:
                check(needle in design,
                      f"{name}: 须按完整身份原位更新,期望含 "
                      f"{needle!r},实际 {design}")
            for needle in forbidden:
                check(needle not in design,
                      f"{name}: 不得出现越界改动 {needle!r},实际 {design}")
            check(applied.get("states", {}).get("synced") is True
                  and applied.get("to_sync") in ([], None),
                  f"{name}: 同步状态须一致收口,实际 {applied}")
            verdict = verify_handoff(retry, {
                SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
                GLOSSARY_REL: read(GLOSSARY_REL),
                RECORD_REL: read(RECORD_REL)})
            check(verdict["ok"], f"{name}: 身份保留后回读应通过,实际 {verdict}")

    with tempfile.TemporaryDirectory() as tmp:
        applied, design, retry, read = _recover_stale_custom_citation(
            tmp, _multiline_link_layout)
        check(f"[每日挑战](\n  {SPEC_REL}\n)（当前 v3）" in design,
              f"multiline-link: 跨行链接结构须原样保留,实际 {design!r}")
        check(f"{SPEC_REL}（当前" not in design,
              f"multiline-link: 不得把版本插进链接目标行,实际 {design!r}")
        check(not (applied.get("states", {}).get("synced") is True
                   and applied.get("to_sync") in ([], None)),
              f"multiline-link: 无法安全更新时不得宣称同步完成,实际 {applied}")
        verdict = verify_handoff(retry, {
            SPEC_REL: read(SPEC_REL), DESIGN_REL: design,
            GLOSSARY_REL: read(GLOSSARY_REL),
            RECORD_REL: read(RECORD_REL)})
        check(not verdict["ok"],
              f"multiline-link: 未完成的同步回读必须失败,实际 {verdict}")


TESTS = (
    test_full_module_handoff_from_adopted_decisions,
    test_missing_key_content_reports_incomplete_without_defaults,
    test_format_only_change_does_not_claim_new_version,
    test_read_only_and_missing_sync_authorization_keep_pending,
    test_history_pending_and_unrelated_content_preserved,
    test_handoff_states_stay_separate_from_implementation_and_playtest,
    test_scope_change_hands_off_without_writing_management_docs,
    test_revised_decision_is_not_inherited_as_synced,
    test_cli_smoke_handoff_entry,
    test_module_sync_keeps_unrelated_baseline_rules,
    test_format_claim_blocks_when_semantics_changed,
    test_after_write_check_failure_does_not_complete_handoff,
    test_english_colon_fingerprints_stay_consistent_after_sync,
    test_partial_spec_write_replans_remaining_baseline_sync,
    test_stale_baseline_citation_recovery_keeps_substantive,
    test_custom_titled_citation_updates_on_recovery,
    test_custom_section_mixed_content_preserved,
    test_same_line_citation_layouts_keep_rules,
    test_reference_boundary_keeps_links_other_modules_and_rules,
    test_citation_identity_keeps_link_targets_longer_names_and_nested_versions,
    test_link_target_parsing_and_version_ownership_keep_valid_citations,
    test_path_identity_and_markdown_boundaries_keep_other_files_and_targets,
    test_link_structure_identity_keeps_labels_targets_and_code_spans,
    test_round14_cross_line_links_complete_identity_and_code_spans,
)


def main() -> int:
    return run_theme("设计问答模块规格交接", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())
