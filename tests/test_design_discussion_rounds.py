#!/usr/bin/env python3
"""统一设计问答框架票 02:识别任务并完成模块问答。

接缝:``plugin/skills/game-design/rounds.py`` 的 ``run_round`` /
``inspect_reply``。只经该 interface 观察行为:把本轮请求、已读事实、
题目目录和开发者回答变成可见回复与决定/未决对应。不测内部函数,
不以 Skill 文本含关键词当作交互通过。期望值来自规格字面量与固定
场景语义,不按实现再算一遍。

    python3 -B tests/test_design_discussion_rounds.py
"""

import json
import sys
from pathlib import Path

from plugin_package_support import PLUGIN_ROOT, REPO_ROOT, make_checker, run_theme

FAILURES, check = make_checker()

SKILL_DIR = PLUGIN_ROOT / "skills" / "game-design"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from rounds import inspect_reply, run_round  # noqa: E402


def _q(qid, title, *, body="", options=None, rec="A", depends_on=None,
       module="每日挑战", priority="normal", open_ended=False, needs_fact=None):
    item = {
        "id": qid,
        "title": title,
        "body": body or f"{title}怎么决定?",
        "options": (
            {} if open_ended else (options or {"A": "方案甲", "B": "方案乙"})
        ),
        "recommendation": rec,
        "reason": f"建议 {rec},因为更贴合当前范围。",
        "depends_on": list(depends_on or []),
        "module": module,
        "priority": priority,
        "open": open_ended,
    }
    if needs_fact:
        item["needs_fact"] = needs_fact
    return item


def test_classifies_new_design_for_missing_module() -> None:
    """齿轮谜城每日挑战:现行设计未覆盖该模块,识别为新设计并写明依据。"""

    result = run_round({
        "request": "想给游戏加每日挑战模式,每天一关。",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "project_stage": "design_only",
        "current_design": {
            "exists": True,
            "covers_request": False,
            "gaps": [],
        },
        "signals": {
            "has_current_design": True,
            "covers_request": False,
            "named_gaps": [],
            "wants_change": False,
            "implementation_mismatches": [],
        },
        "questions": [],
    })
    check(result["classification"]["kind"] == "new_design",
          f"应识别为新设计,实际 {result['classification']}")
    check("现行设计未覆盖" in result["classification"]["rationale"],
          f"依据应说明现行设计未覆盖请求,实际 {result['classification']['rationale']}")
    check("新设计" in result["reply_text"],
          "可见回复应标明识别结果为新设计")


def test_classifies_spec_gap_without_reasking() -> None:
    """已有设计覆盖主题但缺必要规则:补充规格,不重开整套新设计。"""

    result = run_round({
        "request": "连击满五枚之后上限怎么处理,设计里没写清。",
        "goal": "补齐连击上限规则",
        "module": "贝壳连击",
        "project_stage": "implemented",
        "current_design": {
            "exists": True,
            "covers_request": True,
            "gaps": ["连击上限"],
        },
        "settled": {"core-loop": "60 秒限时拾取"},
        "questions": [],
    })
    check(result["classification"]["kind"] == "spec_gap",
          f"应识别为补充规格,实际 {result['classification']}")
    check("补充规格" in result["reply_text"],
          "可见回复应标明补充规格")
    check("新设计" not in result["reply_text"].split("识别：", 1)[-1][:20],
          "补充规格不得写成新设计")


def test_classifies_design_change_for_existing_feature() -> None:
    """潮池海鸥干扰:已有设计上新增干扰,识别为设计变更。"""

    result = run_round({
        "request": "增加海鸥俯冲抢走一枚贝壳。",
        "goal": "讨论海鸥干扰模块",
        "module": "海鸥干扰",
        "project_stage": "implemented",
        "current_design": {
            "exists": True,
            "covers_request": False,
            "wants_change": True,
        },
        "signals": {
            "has_current_design": True,
            "covers_request": False,
            "named_gaps": [],
            "wants_change": True,
            "change_targets": ["海鸥干扰"],
            "implementation_mismatches": [],
        },
        "questions": [],
    })
    check(result["classification"]["kind"] == "design_change",
          f"应识别为设计变更,实际 {result['classification']}")
    check("设计变更" in result["reply_text"],
          "可见回复应标明设计变更")


def test_classifies_implementation_deviation_without_rewriting_design() -> None:
    """设计写持续刷新、实现只生成一次:标明实现偏差,不改写设计。"""

    result = run_round({
        "request": "场上贝壳不刷新,是不是设计要改?",
        "goal": "核对贝壳刷新",
        "module": "基础循环",
        "project_stage": "implemented",
        "current_design": {
            "exists": True,
            "covers_request": True,
            "rules": ["场上持续刷新贝壳"],
        },
        "implementation": {
            "contradicts_design": [
                "设计要求持续刷新,src/main.js 只在开始生成一次",
            ],
        },
        "questions": [],
    })
    check(result["classification"]["kind"] == "implementation_deviation",
          f"应识别为实现偏差,实际 {result['classification']}")
    check(result["rewrite_design"] is False,
          "实现偏差不得擅自改写设计")
    check(result["path"] == "deviation",
          f"实现偏差应走偏差分流,实际 path={result.get('path')}")
    check("实现偏差" in result["reply_text"],
          "可见回复应标明实现偏差")
    check("不通过改写设计" in result["reply_text"]
          or "不擅自改写设计" in result["reply_text"],
          "回复须写明不靠改写设计迁就实现")


def _daily_questions():
    return [
        _q("Q1", "关卡来源", rec="A",
           options={"A": "从现有 20 关按日期抽取", "B": "按日期生成新关"}),
        _q("Q2", "与章节关系", rec="B",
           options={"A": "替代章节", "B": "与章节并存"}),
        _q("Q3", "每日身份", rec="A",
           options={"A": "本机日历日加固定种子", "B": "联网对时"}),
        _q("Q4", "记录", rec="A", depends_on=["Q3"],
           options={"A": "只保留本机当日最佳步数", "B": "联网排行榜"}),
        _q("Q5", "商店定价", module="商业化", rec="A"),
    ]


def test_classifies_covered_request_details_as_spec_gap() -> None:
    """设计已覆盖请求方向但细节未写清:补充规格,不冒充新设计。"""

    result = run_round({
        "request": "每日挑战的入口放在主菜单哪里?",
        "goal": "定每日挑战入口",
        "module": "每日挑战",
        "project_stage": "implemented",
        "current_design": {
            "exists": True,
            "covers_request": True,
            "gaps": [],
        },
        "questions": [_q("Q1", "入口位置", rec="A")],
    })
    check(result["classification"]["kind"] == "spec_gap",
          f"已覆盖请求的待写清细节应识别为补充规格,实际 {result['classification']}")
    check("现行设计未覆盖" not in result["classification"]["rationale"],
          "设计已覆盖请求时依据不得声称未覆盖")


def test_classifies_mixed_request_separately() -> None:
    """同一请求含规格缺口与实现偏差:标混合,分别处理,不重开全部设计。"""

    result = run_round({
        "request": "海鸥规则没写清;另外代码里贝壳不刷新但设计写了持续刷新。",
        "goal": "分流混合请求",
        "module": "海鸥干扰",
        "project_stage": "implemented",
        "signals": {
            "has_current_design": True,
            "covers_request": True,
            "named_gaps": ["海鸥触发频率"],
            "wants_change": False,
            "implementation_mismatches": [
                "设计要求持续刷新,实现只生成一次",
            ],
        },
        "questions": [],
    })
    check(result["classification"]["kind"] == "mixed",
          f"应识别为混合请求,实际 {result['classification']}")
    parts = result["classification"]["parts"]
    check("spec_gap" in parts and "implementation_deviation" in parts,
          f"混合请求应分别列出补充规格与实现偏差,实际 {parts}")
    check(result["rewrite_design"] is False,
          "混合请求中的实现偏差仍不得改写设计")
    check("混合请求" in result["reply_text"],
          "可见回复应标明混合请求")


def test_first_round_asks_ready_questions_and_defers_dependency() -> None:
    """同一模块三项可立即决定、第四项依赖第三项:首轮只问前三项,不混入其他模块。"""

    result = run_round({
        "request": "想给游戏加每日挑战模式。",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "round": 1,
        "current_design": {"exists": True, "covers_request": False},
        "questions": _daily_questions(),
    })
    check(result["shown_ids"] == ["Q1", "Q2", "Q3"],
          f"首轮应完整提出 Q1-Q3,实际 {result['shown_ids']}")
    check(result["deferred_ids"] == ["Q4"],
          f"Q4 应等 Q3 确定后再问,实际 {result['deferred_ids']}")
    check("Q5" not in result["shown_ids"],
          "不得混入无关模块问题")
    check("商业化" not in result["reply_text"],
          "可见回复不得出现无关模块题目")
    check("问题数量：3" in result["reply_text"]
          or "问题数量: 3" in result["reply_text"],
          "轮次开头须标明问题数量 3")
    check("轮次：1" in result["reply_text"] or "轮次: 1" in result["reply_text"],
          "轮次开头须标明轮次")
    check("模块：每日挑战" in result["reply_text"]
          or "模块: 每日挑战" in result["reply_text"],
          "轮次开头须标明当前模块")


def test_round_uses_fixed_question_layout() -> None:
    """每题按 ❓ Q编号｜标题、正文、A/B 选项、➡️ 建议组织,题间分隔。"""

    result = run_round({
        "request": "想给游戏加每日挑战模式。",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "round": 1,
        "current_design": {"exists": True, "covers_request": False},
        "questions": _daily_questions()[:3],
    })
    text = result["reply_text"]
    check("❓ Q1｜关卡来源" in text, "Q1 须使用 ❓ Q1｜标题")
    check("❓ Q2｜与章节关系" in text, "Q2 须使用 ❓ Q2｜标题")
    check("❓ Q3｜每日身份" in text, "Q3 须使用 ❓ Q3｜标题")
    check("选项" in text, "选项须与问题正文分开显示")
    check("- A 从现有 20 关按日期抽取" in text, "选项须带 A 标识")
    check("- B 与章节并存" in text, "选项须带 B 标识")
    check("➡️ 我的建议" in text, "须用 ➡️ 单独标明建议")
    q1 = text.split("❓ Q2", 1)[0]
    check("➡️" in q1, "每题建议须跟在本题内")
    check(text.count("---") >= 2, "题间须有明显分隔")
    verdict = inspect_reply(text, {
        "require_ids": ["Q1", "Q2", "Q3"],
        "forbid_ids": ["Q4"],
        "require_markers": ["❓", "➡️", "选项"],
        "question_count": 3,
    })
    check(verdict["ok"], f"固定排版回复应通过 inspect_reply,实际 {verdict}")


def test_maps_per_question_and_adopt_all_only_shown() -> None:
    """逐题选择与整体采纳只覆盖已展示且指代明确的建议。"""

    questions = _daily_questions()[:3]
    picked = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": questions,
        "shown": ["Q1", "Q2", "Q3"],
        "user_reply": "Q1 选 B，Q2 选 A",
    })
    check(picked["adopted"]["Q1"]["value"] == "B",
          f"Q1 应采纳 B,实际 {picked['adopted']}")
    check(picked["adopted"]["Q1"]["source"] == "user",
          "逐题选择的来源是开发者")
    check(picked["adopted"]["Q2"]["value"] == "A",
          f"Q2 应采纳 A,实际 {picked['adopted']}")
    check("Q3" not in picked["adopted"],
          "未回答的 Q3 不得默认采纳")
    check(picked["pending"]["Q3"]["reason"] == "unanswered",
          f"Q3 应保持待讨论,实际 {picked['pending']}")

    adopted_all = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": questions,
        "shown": ["Q1", "Q2"],
        "user_reply": "整体按建议",
    })
    check(adopted_all["adopted"]["Q1"]["value"] == "A",
          "整体采纳应对已展示 Q1 采用建议 A")
    check(adopted_all["adopted"]["Q2"]["value"] == "B",
          "整体采纳应对已展示 Q2 采用建议 B")
    check(adopted_all["adopted"]["Q1"]["source"] == "recommendation",
          "整体采纳的来源是已展示建议")
    check("Q3" not in adopted_all["adopted"],
          "整体采纳不得覆盖未展示的 Q3")
    check(adopted_all["pending"]["Q3"]["reason"] == "unshown",
          f"未展示题目应标 unshown,实际 {adopted_all['pending']}")


def test_maps_partial_override_freeform_and_vague() -> None:
    """只改一项、自由方案、部分回答和模糊回复:已明确保留,只澄清歧义。"""

    questions = _daily_questions()[:3]
    override = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": questions,
        "shown": ["Q1", "Q2", "Q3"],
        "user_reply": "整体按建议，第 2 项调整为与章节通关后解锁",
    })
    check(override["adopted"]["Q1"]["value"] == "A",
          "整体采纳应保留 Q1 建议")
    check(override["adopted"]["Q3"]["value"] == "A",
          "整体采纳应保留 Q3 建议")
    check(override["adopted"]["Q2"]["value"] == "与章节通关后解锁",
          f"第 2 项应改为自由方案,实际 {override['adopted'].get('Q2')}")
    check(override["adopted"]["Q2"]["source"] == "custom",
          "选项外方案来源为 custom")

    vague = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": questions,
        "shown": ["Q1", "Q2", "Q3"],
        "settled": {"Q1": "A"},
        "user_reply": "可以",
    })
    check(vague["adopted"].get("Q1", {}).get("value") == "A",
          "已明确的 Q1 必须保留")
    check("Q2" not in vague["adopted"] and "Q3" not in vague["adopted"],
          "模糊的「可以」不得批量采纳其他题")
    check(vague["pending"]["Q2"]["reason"] == "ambiguous",
          f"歧义题应只澄清,实际 {vague['pending']}")
    check("✅ 已确定" in vague["reply_text"],
          "回答后应列出已确定")
    check("⏳ 待讨论" in vague["reply_text"],
          "回答后应列出待讨论")


def test_long_group_batches_complete_questions() -> None:
    """超出约 4000 字时按完整问题分批,编号连续;整体采纳不影响未展示题。"""

    pad = "测" * 1800
    questions = [
        _q("Q1", "关卡来源", body=pad + "从哪来关卡?", rec="A"),
        _q("Q2", "与章节关系", body=pad + "和章节什么关系?", rec="B"),
        _q("Q3", "每日身份", body=pad + "如何确定每日关?", rec="A"),
    ]
    result = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": questions,
        "char_limit": 6000,
        "batch_target": 4000,
    })
    batches = result["batches"]
    check(len(batches) == 2, f"三道长题应分成 2 批,实际 {len(batches)}")
    check(batches[0]["ids"] == ["Q1", "Q2"],
          f"第一批应是完整的 Q1+Q2,实际 {batches[0]['ids']}")
    check(batches[1]["ids"] == ["Q3"],
          f"第二批应是完整的 Q3,实际 {batches[1]['ids']}")
    check(batches[0]["ids"] + batches[1]["ids"] == ["Q1", "Q2", "Q3"],
          "分批后编号必须连续且不拆开题目")
    check(len(result["reply_text"]) <= 6000,
          f"当前批可见回复不得超过 6000 字,实际 {len(result['reply_text'])}")
    check(len(batches[0]["text"]) <= 6000, "每批消息不得超过 6000 字")
    check("❓ Q3｜每日身份" not in result["reply_text"],
          "当前可见回复不得包含尚未展示的 Q3")
    check("本批 Q1–Q2" in result["reply_text"] or "本批 Q1-Q2" in result["reply_text"],
          "分批须标出本批覆盖的编号")
    adopted = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": questions,
        "shown": ["Q1", "Q2"],
        "user_reply": "整体按建议",
        "char_limit": 6000,
        "batch_target": 4000,
    })
    check("Q3" not in adopted["adopted"],
          "对当前批整体采纳不得覆盖未展示的 Q3")
    check(adopted["pending"]["Q3"]["reason"] == "unshown",
          "未展示题应保持未采纳")


def test_unknown_and_experience_stay_proposals() -> None:
    """面对「不知道」和体验目标,给出有理由的方案;临时假设不进入已采纳基线。"""

    result = run_round({
        "request": "每日挑战希望轻松一点。",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "experience_goal": "轻松",
        "current_design": {"exists": True, "covers_request": False},
        "questions": [
            _q("Q1", "失败代价",
               options={"A": "失败无惩罚", "B": "失败扣当日进度"},
               rec="B"),
        ],
        "shown": ["Q1"],
        "user_reply": "不知道",
    })
    check("Q1" not in result["adopted"],
          "「不知道」不得把建议写成已采纳")
    check(result["pending"]["Q1"]["reason"] == "unknown",
          f"不知道应保持待讨论,实际 {result['pending']}")
    check("无失败" not in result.get("adopted", {}).get("Q1", {}).get("value", ""),
          "不得把「轻松」直接定为「无失败」")
    check("💡 我的提案" in result["reply_text"],
          "不知道时应给出提案")
    check("失败无惩罚" not in result["reply_text"] or "不是已采纳" in result["reply_text"],
          "临时推演须保持提案身份")
    check(result["statuses"]["proposals"],
          "提案应进入 💡 列表")
    check(not result["statuses"]["determined"],
          "不知道不得产生已确定项")


def test_boundary_revision_updates_later_questions() -> None:
    """边界场景暴露矛盾并明确修正后,后续问题使用修正结果。"""

    result = run_round({
        "request": "海鸥干扰",
        "goal": "讨论海鸥干扰模块",
        "module": "海鸥干扰",
        "current_design": {"exists": True, "wants_change": True},
        "signals": {
            "has_current_design": True,
            "covers_request": False,
            "wants_change": True,
            "change_targets": ["海鸥干扰"],
            "implementation_mismatches": [],
        },
        "settled": {"Q1": "掉在原地"},
        "boundary_revision": {
            "Q1": {
                "from": "掉在原地",
                "to": "掉在俯冲点附近,3 秒内可捡回",
            },
        },
        "questions": [
            _q("Q1", "被抢贝壳去向", module="海鸥干扰", rec="B"),
            _q("Q4", "与连击", module="海鸥干扰", depends_on=["Q1"], rec="A",
               body="被抢后连击如何处理?依赖贝壳去向。"),
        ],
    })
    check(result["adopted"]["Q1"]["value"] == "掉在俯冲点附近,3 秒内可捡回",
          f"后续应使用修正结果,实际 {result['adopted'].get('Q1')}")
    check(result["adopted"]["Q1"].get("replaced") == "掉在原地",
          "旧决定须保留可追溯的替代关系")
    check("掉在俯冲点附近,3 秒内可捡回" in result["reply_text"],
          "后续问题须引用修正后的去向")
    check(result["shown_ids"] == ["Q4"],
          f"依赖已修正的 Q1 后应提出 Q4,实际 {result['shown_ids']}")


def test_authorized_local_tweak_skips_questions() -> None:
    """已授权、无歧义且无连带影响的文案调整走简短流程,不强行提问。"""

    result = run_round({
        "request": "把开始按钮文案改成「出发」。",
        "goal": "调整开始按钮文案",
        "module": "界面文案",
        "current_design": {"exists": True, "covers_request": True},
        "tweak": {
            "kind": "copy",
            "target": "开始按钮",
            "before": "开始",
            "after": "出发",
            "authorized": True,
            "unambiguous": True,
            "side_effects": False,
        },
        "authorization": {"write": True, "product": False, "external": False},
        "questions": [_q("Q1", "是否改文案", module="界面文案")],
    })
    check(result["path"] == "local_tweak",
          f"应走局部微调短流程,实际 path={result['path']}")
    check(result["shown_ids"] == [],
          "局部微调不得强行提问")
    check("全游戏" not in result["reply_text"]
          and "设计地图" not in result["reply_text"],
          "不得重开全游戏地图")
    check("开始" in result["tweak"]["diff"] and "出发" in result["tweak"]["diff"],
          f"须给出文案差异,实际 {result.get('tweak')}")
    check(result["tweak"]["applied"] is True,
          "已授权微调应直接完成差异")

    blocked = run_round({
        "request": "把开始按钮文案改成「出发」,并发布到商店。",
        "goal": "调整开始按钮文案",
        "module": "界面文案",
        "current_design": {"exists": True, "covers_request": True},
        "tweak": {
            "kind": "copy",
            "target": "开始按钮",
            "before": "开始",
            "after": "出发",
            "authorized": True,
            "unambiguous": True,
            "side_effects": False,
        },
        "authorization": {"write": True, "product": False, "external": False},
        "requested_actions": ["publish_store"],
        "questions": [],
    })
    check("publish_store" in blocked["unauthorized_actions"],
          "未授权的外部发布不得执行")
    check(blocked["tweak"]["applied"] is True,
          "已授权的文案差异仍可完成")


def test_game_design_entry_points_to_rounds_seam() -> None:
    """现有高层入口须指向 rounds 接缝;仅 Skill 含关键词不能代替交互核对。"""

    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    check("rounds.py" in text, "Game-Design 入口须指向 rounds.py")
    check("run_round" in text, "Game-Design 入口须使用 run_round")
    check("inspect_reply" in text, "Game-Design 入口须用 inspect_reply 核对可见回复")
    check("不能判为交互通过" in text or "不能当作交互通过" in text,
          "入口须声明仅检查 Skill 文本不能判交互通过")


def test_inspect_reply_rejects_old_unstructured_report() -> None:
    """旧质询报告缺少固定结构时,inspect_reply 不得判通过。"""

    old = (
        REPO_ROOT / "acceptance" / "06-idea-to-current-spec"
        / "evidence" / "w1-report.md"
    ).read_text(encoding="utf-8")
    verdict = inspect_reply(old, {
        "require_ids": ["Q1", "Q2", "Q3"],
        "require_markers": ["❓", "➡️", "选项"],
        "question_count": 3,
    })
    check(verdict["ok"] is False,
          "旧报告缺少 ❓ Q｜与选项结构,不得当作交互通过")
    check(verdict["failures"],
          "失败须指出缺了哪些合同要求")


def test_missing_fact_waits_only_dependent_question() -> None:
    """可查事实未齐时只让依赖它的问题等待,其余前沿继续。"""

    result = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "missing_facts": ["calendar_source"],
        "questions": [
            _q("Q1", "关卡来源", rec="A"),
            _q("Q2", "与章节关系", rec="B"),
            _q("Q3", "每日身份", rec="A", needs_fact="calendar_source"),
        ],
    })
    check(result["shown_ids"] == ["Q1", "Q2"],
          f"不依赖缺失事实的问题应继续,实际 {result['shown_ids']}")
    check(result["deferred_ids"] == ["Q3"],
          f"仅依赖缺失事实的 Q3 应等待,实际 {result['deferred_ids']}")


def test_open_question_does_not_invent_options() -> None:
    """开放问题允许自由回答,不凑选项。"""

    result = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": [
            _q("Q1", "体验一句话", open_ended=True, options=None,
               rec="", body="用一句话描述希望的每日挑战感受。"),
        ],
    })
    check("选项" not in result["reply_text"],
          "开放问题不得凑 A/B 选项")
    check("❓ Q1｜体验一句话" in result["reply_text"],
          "开放问题仍须有 ❓ 编号与标题")


def test_optional_status_icons_only_when_present() -> None:
    """按需显示 🧪 待验证和 🚫 当前不做;空类别不输出。"""

    result = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "to_verify": ["抽关手感是否轻松"],
        "not_now": ["联网排行榜"],
        "questions": [],
    })
    check("🧪 待验证" in result["reply_text"],
          "有待验证项时须显示 🧪")
    check("🚫 当前不做" in result["reply_text"],
          "有当前不做项时须显示 🚫")
    check("抽关手感是否轻松" in result["reply_text"],
          "待验证内容须可见")
    empty = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": [_q("Q1", "关卡来源")],
    })
    check("🧪 待验证" not in empty["reply_text"],
          "没有待验证项时不输出空类别")
    check("🚫 当前不做" not in empty["reply_text"],
          "没有当前不做项时不输出空类别")


def test_negated_or_ambiguous_replies_stay_pending() -> None:
    """否定、二选一未决和「不知道」不得被当成已采纳。"""

    questions = _daily_questions()[:3]
    turn = {
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": questions,
        "shown": ["Q1", "Q2", "Q3"],
    }
    refused = run_round({**turn, "user_reply": "不要整体按建议，先讨论"})
    check("Q1" not in refused["adopted"],
          f"否定整体建议不得采纳 Q1,实际 {refused['adopted']}")
    check(refused["pending"].get("Q1", {}).get("reason") in
          {"unanswered", "ambiguous"},
          f"否定后 Q1 须保持待讨论,实际 {refused['pending']}")

    unsure = run_round({**turn, "user_reply": "Q1 选 A 还是 B，我还没决定"})
    check("Q1" not in unsure["adopted"],
          f"未决定的二选一不得采纳 Q1,实际 {unsure['adopted']}")
    check("Q1" in unsure["pending"],
          f"未决定的 Q1 须保持待讨论,实际 {unsure['pending']}")

    unknown = run_round({**turn, "user_reply": "Q1：不知道"})
    check("Q1" not in unknown["adopted"],
          f"「不知道」不得写成自定决定,实际 {unknown['adopted']}")
    check(unknown["pending"].get("Q1", {}).get("reason") == "unknown",
          f"Q1 不知道应保持提案待讨论,实际 {unknown['pending']}")

    cannot = run_round({**turn, "user_reply": "不能整体按建议，先讨论"})
    check(cannot["adopted"] == {},
          f"「不能整体按建议」不得写成三题采纳,实际 {cannot['adopted']}")
    check("Q1" in cannot["pending"] and "Q2" in cannot["pending"]
          and "Q3" in cannot["pending"],
          f"否定后三题须保持待讨论,实际 {cannot['pending']}")

    local_unknown = run_round({**turn, "user_reply": "整体按建议，Q1：不知道"})
    check("Q1" not in local_unknown["adopted"],
          f"整体采纳后的局部不知道须覆盖 Q1,实际 {local_unknown['adopted']}")
    check(local_unknown["pending"].get("Q1", {}).get("reason") == "unknown",
          f"Q1 不知道应保持待讨论,实际 {local_unknown['pending']}")
    check("Q2" in local_unknown["adopted"] and "Q3" in local_unknown["adopted"],
          f"未声明例外的题目仍可整体采纳,实际 {local_unknown['adopted']}")


def test_later_ambiguity_does_not_drop_earlier_answers() -> None:
    """后题歧义只澄清该题,不得吞掉前题已经明确的答案。"""

    questions = _daily_questions()[:3]
    result = run_round({
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": questions,
        "shown": ["Q1", "Q2", "Q3"],
        "user_reply": "Q1 选 A，Q2 选 A 还是 B，我还没决定",
    })
    check(result["adopted"].get("Q1", {}).get("value") == "A",
          f"明确的 Q1 选 A 必须保留,实际 {result['adopted']}")
    check("Q2" not in result["adopted"],
          f"Q2 二选一未决不得采纳,实际 {result['adopted']}")
    check("Q2" in result["pending"],
          f"Q2 须保持待讨论,实际 {result['pending']}")
    check("Q3" not in result["adopted"],
          "未回答的 Q3 不得被后题歧义连带默认")


def test_combined_reservations_override_overall_adopt() -> None:
    """整体采纳中的含糊例外,以及「不是整体按建议」,都不得写成已采纳。"""

    questions = _daily_questions()[:3]
    turn = {
        "request": "每日挑战",
        "goal": "形成每日挑战核心模块",
        "module": "每日挑战",
        "current_design": {"exists": True, "covers_request": False},
        "questions": questions,
        "shown": ["Q1", "Q2", "Q3"],
    }
    mixed = run_round({
        **turn, "user_reply": "整体按建议，Q2 选 A 还是 B，我还没决定"})
    check("Q2" not in mixed["adopted"],
          f"整体采纳中的 Q2 含糊例外不得采纳,实际 {mixed['adopted']}")
    check("Q2" in mixed["pending"],
          f"Q2 含糊例外须保持待讨论,实际 {mixed['pending']}")
    check("Q1" in mixed["adopted"] and "Q3" in mixed["adopted"],
          f"未声明例外的题目仍可整体采纳,实际 {mixed['adopted']}")

    negated = run_round({**turn, "user_reply": "不是整体按建议，先讨论"})
    check(negated["adopted"] == {},
          f"「不是整体按建议」不得保存推荐,实际 {negated['adopted']}")
    check("Q1" in negated["pending"] and "Q2" in negated["pending"]
          and "Q3" in negated["pending"],
          f"否定后三题须保持待讨论,实际 {negated['pending']}")

    colon = run_round({
        **turn, "user_reply": "整体按建议，Q2：选 A 还是 B，我还没决定"})
    check("Q2" not in colon["adopted"],
          f"冒号后的含糊选择不得写成自定采纳,实际 {colon['adopted']}")
    check("Q2" in colon["pending"],
          f"Q2 冒号含糊例外须保持待讨论,实际 {colon['pending']}")


def main() -> int:
    return run_theme("设计问答模块识别与成组交互", (
        test_classifies_new_design_for_missing_module,
        test_classifies_spec_gap_without_reasking,
        test_classifies_design_change_for_existing_feature,
        test_classifies_covered_request_details_as_spec_gap,
        test_classifies_implementation_deviation_without_rewriting_design,
        test_classifies_mixed_request_separately,
        test_first_round_asks_ready_questions_and_defers_dependency,
        test_round_uses_fixed_question_layout,
        test_maps_per_question_and_adopt_all_only_shown,
        test_maps_partial_override_freeform_and_vague,
        test_long_group_batches_complete_questions,
        test_unknown_and_experience_stay_proposals,
        test_boundary_revision_updates_later_questions,
        test_authorized_local_tweak_skips_questions,
        test_game_design_entry_points_to_rounds_seam,
        test_inspect_reply_rejects_old_unstructured_report,
        test_missing_fact_waits_only_dependent_question,
        test_open_question_does_not_invent_options,
        test_optional_status_icons_only_when_present,
        test_negated_or_ambiguous_replies_stay_pending,
        test_later_ambiguity_does_not_drop_earlier_answers,
        test_combined_reservations_override_overall_adopt,
    ), FAILURES)


if __name__ == "__main__":
    sys.exit(main())
