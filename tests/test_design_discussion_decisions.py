#!/usr/bin/env python3
"""统一设计问答框架票 03:即时保存决定并恢复讨论。

接缝:``plugin/skills/game-design/decisions.py`` 的 ``plan_save`` /
``plan_sync`` / ``apply_save`` / ``verify_saved`` / ``restore_from_records``。
保存证据一律经真实受控写入通道(``mgs_runtime.GateService``,与 mgs-gate
相同的逐次权限与版本校验)落到临时项目记录文件,再直接回读文件核对;
不用自述代替实际保存证据。期望值来自工单与规格字面量,不测内部函数。

    python3 -B tests/test_design_discussion_decisions.py
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from plugin_package_support import PLUGIN_ROOT, make_checker, run_theme
from runtime_gate_support import GateService, mcp_gate

FAILURES, check = make_checker()

SKILL_DIR = PLUGIN_ROOT / "skills" / "game-design"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from decisions import (  # noqa: E402
    apply_save, plan_save, plan_sync, restore_from_records, verify_saved,
)
from rounds import run_round  # noqa: E402

RECORD_REL = "docs/mygamestudio/records/decisions-每日挑战.md"
DATE = "2026-09-14"


def _service(root: Path):
    """临时项目 + 真实受控通道服务(设计角色可写记录目录)。"""

    project = root / "project"
    (project / "docs/mygamestudio/records").mkdir(parents=True)
    (project / "docs/mygamestudio/GAME_DESIGN.md").write_text("DESIGN v1\n")
    svc = GateService(root / "runtime")
    svc.init_policy(
        project_root=project,
        roles={
            "design": ["docs/mygamestudio/records/**",
                       "docs/mygamestudio/GAME_DESIGN.md"],
        },
        purposes={"design_discussion": ["docs/mygamestudio/records/**"]},
    )
    return svc, project


def _instance(svc, resources=None):
    return svc.create_instance(
        role="design", task="G02", purpose="design_discussion",
        resources=list(resources or ["docs/mygamestudio/records/**"]),
        ttl_seconds=1800)


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


class _McpChannel:
    """真实 mgs-gate 工具入口适配:mgs_scope / mgs_write 的 MCP 处理函数。"""

    def __init__(self, svc, token):
        self.svc = svc
        self.token = token
        self.calls = []

    @staticmethod
    def _payload(result):
        return json.loads(result["content"][0]["text"])

    def scope(self):
        self.calls.append("mgs_scope")
        return self._payload(mcp_gate.handle_tools_call(
            self.svc, "mgs_scope", {"token": self.token}))

    def write(self, path, content, expected_sha256=None, note=None):
        self.calls.append("mgs_write")
        args = {"token": self.token, "path": path, "content": content,
                "note": note}
        if expected_sha256 is not None:
            args["expected_sha256"] = expected_sha256
        return self._payload(mcp_gate.handle_tools_call(
            self.svc, "mgs_write", args))


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
         "impact": "影响存档结构。"},
        {"id": "Q5", "title": "商店定价", "body": "定价多少?",
         "options": {"A": "6 元", "B": "免费加广告"}, "recommendation": "A",
         "reason": "小体量一次买断更清楚。", "module": "商业化"},
    ]


def _turn(reply, *, round_no=1, settled=None, shown=None, module="每日挑战"):
    return {
        "request": "想给游戏加每日挑战模式,每天一关。",
        "goal": "形成每日挑战核心模块",
        "module": module,
        "round": round_no,
        "current_design": {"exists": True, "covers_request": False},
        "questions": _questions(),
        "shown": list(shown or ["Q1", "Q2", "Q3"]),
        "settled": dict(settled or {}),
        "user_reply": reply,
    }


def _meta(*, round_no=1, write=True, reply="Q1 选 B，Q2 选 A", evidence=None,
          path=RECORD_REL, module="每日挑战"):
    meta = {"record_path": path, "module": module, "round": round_no,
            "date": DATE, "decider": "开发者",
            "authorization": {"write": write}, "reply": reply}
    if evidence is not None:
        meta["evidence"] = evidence
    return meta


def test_normal_save_matches_shown_questions_and_reads_back() -> None:
    """正常保存:本轮答案对应展示题目与建议,落盘并经回读核对。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        channel = _Channel(svc, _instance(svc).token)
        read = _reader(project)
        reply = "Q1 选 B，Q2 选 A"
        turn_result = run_round(_turn(reply))
        plan = plan_save(None, turn_result, _meta(reply=reply))
        check(plan["status"] == "planned", f"有授权且目标不存在时应可计划,实际 {plan['status']}")
        check(plan["expected_sha256"] == "absent",
              f"新建记录的目标版本应为 absent,实际 {plan['expected_sha256']}")
        check(plan["precheck"]["target_version"] == "absent"
              and plan["precheck"]["history"]["decisions"] == 0,
              f"写入前须核对目标版本与相关历史,实际 {plan['precheck']}")
        text = plan["content"]
        for needle in (
            "# 每日挑战：决定记录",
            "## 第 1 轮 2026-09-14",
            "用户回复：「Q1 选 B，Q2 选 A」",
            "决定者：开发者。日期：2026-09-14。",
            "- D 每日挑战·Q1 关卡来源：采纳 B 每日生成新关",
            "- D 每日挑战·Q2 与章节关系：采纳 A 替代章节",
            "建议出处：本轮 ➡️ 建议 A 从现有 20 关按日期抽取（开发者选择 B）",
            "影响：决定每日关的复用方式;记录规则依赖它。",
            "同步状态：待同步",
            "Q3 每日身份：未回答",
            "Q4 记录：依赖未满足",
        ):
            check(needle in text, f"本轮最小记录应包含 {needle!r}")
        check("·Q3 每日身份：采纳" not in text,
              "未回答题的助手建议不得冒充用户决定")
        check("·Q5" not in text, "无关模块的问题不得写入本模块记录")

        applied = apply_save(plan, channel, read)
        check(applied["status"] == "saved", f"应保存成功,实际 {applied['status']}")
        check(applied["saved"] is True, "回读核对通过才可称为已保存")
        check(applied["next_round_ready"] is True,
              "保存完成后才允许进入依赖这些答案的下一轮")
        check(len(channel.writes) == 1, "一次保存只经一次受控写入")
        check(channel.scopes and channel.scopes[0]["decision"] == "allow",
              f"写入前须核对本次授权,实际 {channel.scopes}")
        on_disk = read(RECORD_REL)
        check(on_disk == text, "落盘内容必须与本轮最小记录一致")
        check(applied["states"]["Q1"]["saved"] is True
              and applied["states"]["Q1"]["synced"] is False,
              f"决定已保存但基线未同步,实际 {applied['states'].get('Q1')}")
        check(applied["to_sync"] == ["Q1", "Q2"],
              f"待同步内容应可定位,实际 {applied['to_sync']}")
        check("已保存" in applied["report"] and "待同步" in applied["report"],
              f"报告须区分已保存与待同步,实际 {applied['report']}")
        check("未实现" in applied["report"] and "未验证" in applied["report"],
              "未提供实现或验证证据时须如实标未实现、未验证")
        check(RECORD_REL in applied["report"], "报告须给出记录位置")
        verdict = verify_saved(plan, on_disk)
        check(verdict["ok"], f"回读核对应通过,实际 {verdict}")


def test_partial_answer_records_open_items_and_reuses_module_record() -> None:
    """部分回答:未回答保持未决并沿用同一模块记录,不按 Q 新建文件。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        channel = _Channel(svc, _instance(svc).token)
        read = _reader(project)
        first = run_round(_turn("Q1 选 B"))
        applied = apply_save(plan_save(None, first, _meta(reply="Q1 选 B")),
                             channel, read)
        check(applied["status"] == "saved", f"部分回答也应保存已明确部分,实际 {applied}")
        text = read(RECORD_REL)
        check("- D 每日挑战·Q1 关卡来源：采纳 B 每日生成新关" in text,
              "已明确部分须落盘")
        check("·Q2 与章节关系：采纳" not in text, "未回答不得写成已采纳")
        check("Q2 与章节关系：未回答" in text, "未回答须记为未决")
        check("Q3 每日身份：未回答" in text, "未回答须记为未决")
        check("Q4 记录：依赖未满足" in text, "依赖未满足的前置决定须标明")

        second_reply = "Q2 选 A，Q3 选 B"
        second_turn = run_round(_turn(second_reply, round_no=2,
                                      settled={"Q1": "B"},
                                      shown=["Q2", "Q3"]))
        plan2 = plan_save(text, second_turn,
                          _meta(round_no=2, reply=second_reply))
        check(plan2["status"] == "planned", f"第二轮应可继续计划,实际 {plan2}")
        check(plan2["expected_sha256"] != "absent",
              "沿用已有记录位置时应带目标当前版本")
        check(plan2["precheck"]["history"]["decisions"] == 1,
              "写入前须核对已有决定历史")
        check("## 第 1 轮 2026-09-14" in plan2["content"]
              and "## 第 2 轮 2026-09-14" in plan2["content"],
              "第二轮须追加在同一记录且保留第一轮历史")
        applied2 = apply_save(plan2, channel, read)
        check(applied2["status"] == "saved", f"第二轮保存应成功,实际 {applied2}")
        files = sorted(p.name for p in
                       (project / "docs/mygamestudio/records").glob("*.md"))
        check(files == ["decisions-每日挑战.md"],
              f"同一模块沿用已有记录位置,不为每题新建文件,实际 {files}")
        final = read(RECORD_REL)
        check(final.count("- D 每日挑战·") == 3,
              f"两轮共三项决定,实际 {final.count('- D 每日挑战·')}")
        check("Q4 记录：依赖未满足" in final, "第一轮未决历史须保留")


def test_repeated_same_answer_creates_no_duplicate() -> None:
    """同一次回答重复处理不重复创建决定,也不再次写入。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        channel = _Channel(svc, _instance(svc).token)
        read = _reader(project)
        reply = "Q1 选 B，Q2 选 A"
        turn_result = run_round(_turn(reply))
        saved = apply_save(plan_save(None, turn_result, _meta(reply=reply)),
                           channel, read)
        check(saved["status"] == "saved", "首次保存应成功")
        before = read(RECORD_REL)
        again = plan_save(before, turn_result, _meta(reply=reply))
        check(again["status"] == "no_new",
              f"同一次回答重复处理不得产生新决定,实际 {again['status']}")
        check([item["qid"] for item in again["duplicates"]] == ["Q1", "Q2"],
              f"重复项须如实列出,实际 {again['duplicates']}")
        check(again["content"] == before, "重复处理不得改写记录内容")
        applied = apply_save(again, channel, read)
        check(applied["status"] == "no_new" and applied["saved"] is True,
              f"重复处理仍是已保存状态,实际 {applied['status']}")
        check(len(channel.writes) == 1, "重复处理不得再次提交写入")
        after = read(RECORD_REL)
        check(after == before, "重复处理后记录保持不变")
        check(after.count("·Q1 关卡来源：采纳") == 1,
              "同一次回答不得重复创建决定")


def test_changed_decision_keeps_history_and_replacement() -> None:
    """用户改口:保留旧含义与替代关系,不覆盖其他仍有效的决定。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        channel = _Channel(svc, _instance(svc).token)
        read = _reader(project)
        reply = "Q1 选 B，Q2 选 A"
        apply_save(plan_save(None, run_round(_turn(reply)), _meta(reply=reply)),
                   channel, read)
        revised_reply = "Q1 调整为 每日生成新关"
        revised = run_round(_turn(revised_reply, round_no=2,
                                  settled={"Q1": "B", "Q2": "A"}))
        plan = plan_save(read(RECORD_REL), revised,
                         _meta(round_no=2, reply=revised_reply))
        text = plan["content"]
        check("- D 每日挑战·Q1 关卡来源：采纳 每日生成新关" in text,
              f"须写入修正后的决定,实际 {text}")
        check("- D 每日挑战·Q1 关卡来源：采纳 B 每日生成新关" in text,
              "旧含义须保留在历史中,不得被覆盖")
        check("替代：「B 每日生成新关」（第 1 轮，历史保留）" in text,
              "须记录替代关系")
        check("已被替代" in text, "旧决定须标明已被替代")
        check(text.count("·Q2 与章节关系：采纳 A 替代章节") == 1
              and "·Q2 与章节关系：采纳 A 替代章节（已被替代）" not in text
              and text.count("（已被替代）") == 1,
              "其他有效决定不得被覆盖或误标替代")
        applied = apply_save(plan, channel, read)
        check(applied["status"] == "saved", f"改口保存应成功,实际 {applied}")
        check("·Q2 与章节关系：采纳 A 替代章节" in read(RECORD_REL),
              "其他决定须保留")
        state = restore_from_records({RECORD_REL: read(RECORD_REL)}, "每日挑战")
        check(state["decisions"]["Q1"]["value"] == "每日生成新关",
              f"修正后应以新值为当前有效决定,实际 {state['decisions']['Q1']}")
        check([item["value"] for item in state["superseded"]] == ["B 每日生成新关"],
              f"旧决定须可追溯,实际 {state['superseded']}")
        check([item["value"] for item in state["decisions"].values()
               if item["qid"] == "Q2"] == ["A 替代章节"],
              "其他决定不受改口影响")

        # 旧回答重放:已被后续用户修改取代,不得覆盖后来的用户修改
        replay_reply = "Q1 选 B"
        replay = run_round(_turn(replay_reply, round_no=1,
                                 settled={"Q2": "A"},
                                 shown=["Q2", "Q3"]))
        stale = plan_save(read(RECORD_REL), replay,
                          _meta(round_no=1, reply=replay_reply))
        check(stale["status"] == "no_new",
              f"重放旧回答不得产生决定,实际 {stale['status']}")
        check([item["qid"] for item in stale["protected"]] == ["Q1"],
              f"被后来修改取代的答案须如实列出,实际 {stale['protected']}")
        stale_applied = apply_save(stale, channel, read)
        check(stale_applied["saved"] is True
              and "未覆盖" in stale_applied["report"],
              f"报告须说明未覆盖后来的修改,实际 {stale_applied['report']}")
        final = read(RECORD_REL)
        check("·Q1 关卡来源：采纳 每日生成新关" in final
              and "·Q1 关卡来源：采纳 B 每日生成新关（已被替代）" in final,
              "后来的用户修改不得被旧答案回退")


def test_read_only_unsaved_and_restore_prevents_reasking() -> None:
    """只读讨论明确未保存;恢复后可定位待同步,已保存的决定不重问。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        channel = _Channel(svc, _instance(svc).token)
        read = _reader(project)
        reply = "Q1 选 B，Q2 选 A"
        turn_result = run_round(_turn(reply))

        read_only = plan_save(None, turn_result, _meta(write=False, reply=reply))
        check(read_only["status"] == "read_only",
              f"无写入授权时应只读,实际 {read_only['status']}")
        blocked = apply_save(read_only, channel, read)
        check(blocked["saved"] is False and blocked["status"] == "read_only",
              f"只读讨论不得写入,实际 {blocked['status']}")
        check("只读" in blocked["report"] and "未保存" in blocked["report"],
              f"报告须说明只读且尚未保存,实际 {blocked['report']}")
        check(len(channel.writes) == 0, "只读讨论不得提交任何写入")
        check(read(RECORD_REL) is None, "只读讨论不得留下记录文件")
        check(blocked["adopted"]["Q1"] == "B",
              "已采纳事实须保留,等待授权后保存")

        applied = apply_save(plan_save(None, turn_result, _meta(reply=reply)),
                             channel, read)
        check(applied["status"] == "saved", "授权后应能保存")
        state = restore_from_records({RECORD_REL: read(RECORD_REL)}, "每日挑战")
        check(state["settled"] == {"Q1": "B 每日生成新关", "Q2": "A 替代章节"},
              f"恢复须给出已定内容,实际 {state['settled']}")
        check(state["to_sync"] == ["Q1", "Q2"] and state["sync_pending"] is True,
              f"已保存未同步的内容须可定位,实际 {state['to_sync']}")
        check(state["baseline_synced"] is False,
              "尚未同步核心基线时不得当作已同步基线")
        check(RECORD_REL in state["report"], "恢复报告须给出待同步内容的位置")
        check("待同步" in state["report"], "恢复报告须标明待同步")

        nxt = run_round(_turn("", settled=state["settled"]))
        check("Q1" not in nxt["shown_ids"] and "Q2" not in nxt["shown_ids"],
              f"已保存的决定不得重问,实际 {nxt['shown_ids']}")
        check(nxt["shown_ids"] == ["Q3"],
              f"下一轮只问仍未定的题目,实际 {nxt['shown_ids']}")

        sync_meta = {"record_path": RECORD_REL, "module": "每日挑战",
                     "date": DATE, "qids": ["Q1"],
                     "sync_ref": "GAME_DESIGN v2",
                     "authorization": {"write": True, "sync": True}}
        sync_plan = plan_sync(read(RECORD_REL), sync_meta)
        check(sync_plan["status"] == "planned",
              f"有同步授权时应可标记已同步,实际 {sync_plan}")
        check("同步状态：已同步（2026-09-14，GAME_DESIGN v2）" in sync_plan["content"],
              "同步标记须写明日期与目标版本")
        sync_applied = apply_save(sync_plan, channel, read)
        check(sync_applied["status"] == "saved",
              f"同步状态更新应落盘,实际 {sync_applied}")
        state2 = restore_from_records({RECORD_REL: read(RECORD_REL)}, "每日挑战")
        check(state2["to_sync"] == ["Q2"],
              f"Q1 已同步后只剩 Q2 待同步,实际 {state2['to_sync']}")
        check(state2["decisions"]["Q1"]["synced"] is True
              and state2["decisions"]["Q2"]["synced"] is False,
              "已同步与待同步须分别记录")
        unsynced = plan_sync(read(RECORD_REL),
                             {**sync_meta, "authorization": {"write": True}})
        check(unsynced["status"] == "unauthorized",
              f"缺少同步授权时须保留待同步项,实际 {unsynced['status']}")


def test_conflict_denied_and_unconfirmed_report_true_state() -> None:
    """版本冲突、授权拒绝与回读失败:报告真实状态,不称已保存,不绕行保障。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        channel = _Channel(svc, _instance(svc).token)
        read = _reader(project)
        reply = "Q1 选 B，Q2 选 A"
        apply_save(plan_save(None, run_round(_turn(reply)), _meta(reply=reply)),
                   channel, read)
        target = project / RECORD_REL
        before = read(RECORD_REL)
        new_reply = "Q2 调整为 与章节并存"
        rr2 = run_round(_turn(new_reply, round_no=2, settled={"Q1": "B"}))

        # 写入前核对发现目标已被外部改动:拒绝覆盖,先重新读取
        plan_conflict = plan_save(before, rr2,
                                  _meta(round_no=2, reply=new_reply))
        target.write_text(before + "- 外部修改：他人补充说明\n")
        conflicted = apply_save(plan_conflict, channel, read)
        check(conflicted["status"] == "conflict"
              and conflicted["rule_stage"] == "version",
              f"目标已变时须报版本冲突,实际 {conflicted['status']}")
        check(conflicted["saved"] is False
              and "版本冲突" in conflicted["report"]
              and "未保存" in conflicted["report"],
              f"冲突时报告须说明未保存,实际 {conflicted['report']}")
        check(len(channel.writes) == 1,
              "预检已发现目标变化时不得提交覆盖写入")
        check("外部修改" in target.read_text(), "外部改动不得被旧快照覆盖")

        # 过期缓存视图:预检通过,通道逐次版本校验仍拒绝
        cached = before

        def cached_read(path):
            return cached

        stale_plan = plan_save(cached, rr2, _meta(round_no=2, reply=new_reply))
        stale = apply_save(stale_plan, channel, cached_read)
        check(stale["rule_stage"] == "version" and stale["saved"] is False,
              f"缓存结果不得替代逐次版本校验,实际 {stale}")
        check(len(channel.writes) == 2,
              "缓存视图下由受控通道逐次校验作出拒绝")
        check("外部修改" in target.read_text(), "通道拒绝后目标字节保持不变")

        # 重新读取实际记录与版本后可继续
        fresh = plan_save(read(RECORD_REL), rr2,
                          _meta(round_no=2, reply=new_reply))
        check(fresh["status"] == "planned"
              and fresh["expected_sha256"] != plan_conflict["expected_sha256"],
              "重新计划须使用当前实际版本")
        continued = apply_save(fresh, channel, read)
        check(continued["status"] == "saved", f"重读后保存应成功,实际 {continued}")
        check("外部修改" in target.read_text(), "重新保存须保留外部改动")

        # 任务授权之外:受控通道拒绝,报告拒绝依据,不换路径重试
        limited = _Channel(
            svc, _instance(svc,
                           resources=["docs/mygamestudio/GAME_DESIGN.md"]).token)
        reply3 = "Q3 选 A"
        rr3 = run_round(_turn(reply3, round_no=3,
                              settled={"Q1": "B", "Q2": "与章节并存"},
                              shown=["Q3"]))
        plan3 = plan_save(read(RECORD_REL), rr3,
                          _meta(round_no=3, reply=reply3))
        denied = apply_save(plan3, limited, read)
        check(denied["status"] == "denied"
              and denied["rule_stage"] == "task_grant",
              f"授权外写入应被受控通道拒绝,实际 {denied}")
        check(denied["saved"] is False and "未保存" in denied["report"]
              and "task_grant" in denied["report"],
              "拒绝须报告真实状态与依据")
        check(len(limited.writes) == 1, "越界写入被拒后不得换路径重试")

        # 授权已撤销:不得使用缓存权限,不再提交写入
        inst2 = _instance(svc)
        revoked = _Channel(svc, inst2.token)
        svc.release_instance(inst2.instance_id)
        revoked_result = apply_save(plan3, revoked, read)
        check(revoked_result["status"] == "denied"
              and revoked_result["rule_stage"] == "identity",
              f"撤销授权后须重新核对并拒绝,实际 {revoked_result}")
        check(len(revoked.writes) == 0, "授权已撤销时不得提交写入")

        # 写入后回读失败:不得称为已保存
        calls = {"n": 0}

        def flaky(path):
            if path == RECORD_REL:
                calls["n"] += 1
                if calls["n"] > 1:
                    return None
            return read(path)

        unconfirmed = apply_save(plan3, channel, flaky)
        check(unconfirmed["status"] == "save_unconfirmed"
              and unconfirmed["saved"] is False,
              f"未回读成功不得称已保存,实际 {unconfirmed['status']}")
        check("未确认" in unconfirmed["report"]
              and "回读" in unconfirmed["report"],
              f"报告须说明回读未成功,实际 {unconfirmed['report']}")


def test_resume_after_interruption_keeps_valid_parts() -> None:
    """回答后模块结束前中断:恢复先读实际记录与版本,只续未完成部分。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        channel = _Channel(svc, _instance(svc).token)
        read = _reader(project)
        apply_save(plan_save(None, run_round(_turn("Q1 选 B")),
                             _meta(reply="Q1 选 B")), channel, read)

        text = read(RECORD_REL)
        state = restore_from_records({RECORD_REL: text}, "每日挑战")
        check(state["settled"] == {"Q1": "B 每日生成新关"},
              f"恢复须先读实际记录,实际 {state['settled']}")
        check([item["qid"] for item in state["pending"]] == ["Q2", "Q3", "Q4"],
              f"未决内容须保留,实际 {state['pending']}")
        check([item["status"] for item in state["pending"]]
              == ["未回答", "未回答", "依赖未满足"],
              f"未决原因须保留,实际 {state['pending']}")
        nxt = run_round(_turn("", settled=state["settled"]))
        check("Q1" not in nxt["shown_ids"], "恢复后不得重问已保存的决定")
        check(nxt["shown_ids"] == ["Q2", "Q3"],
              f"只继续未完成部分,实际 {nxt['shown_ids']}")

        target = project / RECORD_REL
        target.write_text(text + "- D 每日挑战·Q1 关卡来源：采纳 A 从现有 20 关按日期抽取\n")
        state2 = restore_from_records({RECORD_REL: target.read_text()}, "每日挑战")
        check(state2["decisions"]["Q1"]["value"] == "A 从现有 20 关按日期抽取",
              "外部修改后须以实际记录为准,不恢复旧快照")
        check([item["value"] for item in state2["superseded"]] == ["B 每日生成新关"],
              f"旧决定保留为历史,实际 {state2['superseded']}")
        rr = run_round(_turn("Q2 选 A", round_no=2,
                             settled=state2["settled"], shown=["Q2", "Q3"]))
        plan = plan_save(target.read_text(), rr,
                         _meta(round_no=2, reply="Q2 选 A"))
        applied = apply_save(plan, channel, read)
        check(applied["status"] == "saved", f"续做部分应能保存,实际 {applied}")
        files = sorted(p.name for p in
                       (project / "docs/mygamestudio/records").glob("*.md"))
        check(files == ["decisions-每日挑战.md"], f"仍沿用同一记录,实际 {files}")
        final = restore_from_records({RECORD_REL: read(RECORD_REL)}, "每日挑战")
        check(final["settled"]["Q1"] == "A 从现有 20 关按日期抽取",
              "恢复保存不得覆盖外部修改")
        check("Q3 每日身份：未回答" in read(RECORD_REL),
              "仍未完成的部分须保留为未决")


def test_states_do_not_conflate_saved_synced_implemented_verified() -> None:
    """已采纳、已保存、已同步、已实现与已验证须分别记录,不自动推定。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        channel = _Channel(svc, _instance(svc).token)
        read = _reader(project)
        reply = "Q1 选 B，Q2 选 A"
        rr = run_round(_turn(reply))
        evidence = {"Q1": {"implemented": True, "verified": False}}
        applied = apply_save(plan_save(None, rr, _meta(reply=reply,
                                                       evidence=evidence)),
                             channel, read)
        check(applied["status"] == "saved", "正常保存应成功")
        states = applied["states"]
        check(states["Q1"]["saved"] is True and states["Q1"]["synced"] is False,
              f"Q1 已保存但未同步,实际 {states['Q1']}")
        check(states["Q1"]["implemented"] is True
              and states["Q1"]["verified"] is False,
              f"Q1 仅实现了尚未验证,实际 {states['Q1']}")
        check(states["Q2"]["implemented"] is False
              and states["Q2"]["verified"] is False,
              "无证据的决定不得标已实现或已验证")
        check("已保存" in applied["report"] and "待同步" in applied["report"]
              and "已实现" in applied["report"]
              and "未验证" in applied["report"],
              f"报告须分别表达各状态,实际 {applied['report']}")
        record = read(RECORD_REL)
        check("已实现" not in record and "已验证" not in record,
              "记录只承载决定与同步状态,不据此宣称实现或验证")

        plain_channel = _Channel(svc, _instance(svc).token)
        plain = apply_save(plan_save(None, rr, _meta(reply=reply,
                                                     path=RECORD_REL + ".plain")),
                           plain_channel, read)
        check(plain["status"] == "saved", "无证据时也应正常保存")
        check("未实现" in plain["report"] and "未验证" in plain["report"]
              and "已实现" not in plain["report"],
              f"没有实现证据时不得出现已实现,实际 {plain['report']}")


def test_mcp_gate_tool_entry_saves_and_denies() -> None:
    """经真实 mgs-gate 工具入口(mgs_scope/mgs_write):授权内保存、越界拒绝。"""

    with tempfile.TemporaryDirectory() as tmp:
        svc, project = _service(Path(tmp))
        read = _reader(project)
        channel = _McpChannel(svc, _instance(svc).token)
        reply = "Q1 选 B，Q2 选 A"
        applied = apply_save(
            plan_save(None, run_round(_turn(reply)), _meta(reply=reply)),
            channel, read)
        check(applied["status"] == "saved",
              f"经 MCP 工具入口应保存成功,实际 {applied['status']}")
        check(channel.calls == ["mgs_scope", "mgs_write"],
              f"提交须先核对范围再写入,实际 {channel.calls}")
        check(applied["channel_result"]["decision"] == "allow",
              "通道返回应为 allow")
        check("- D 每日挑战·Q1 关卡来源：采纳 B 每日生成新关" in read(RECORD_REL),
              "MCP 入口保存须留下实际记录")

        def flaky_reader(path):
            return read(path)

        limited = _McpChannel(
            svc, _instance(svc,
                           resources=["docs/mygamestudio/GAME_DESIGN.md"]).token)
        denied = apply_save(
            plan_save(read(RECORD_REL),
                      run_round(_turn("Q3 选 A", round_no=2,
                                      settled={"Q1": "B", "Q2": "A"},
                                      shown=["Q3"])),
                      _meta(round_no=2, reply="Q3 选 A")),
            limited, flaky_reader)
        check(denied["status"] == "denied"
              and denied["rule_stage"] == "task_grant",
              f"越界写入须经 MCP 入口被拒,实际 {denied['status']}")
        check(channel.calls.count("mgs_write") == 1,
              "被拒后不得重复提交或换路径重试")


def test_cli_smoke_and_entry_points_to_seam() -> None:
    """CLI 冒烟:经真实受控通道按固定会话顺序覆盖七类场景,留存实际记录作证。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        inst = _instance(svc)
        cli = str(SKILL_DIR / "decisions_cli.py")
        records_dir = project / "docs/mygamestudio/records"

        def run_cli(action, payload, *args):
            return subprocess.run(
                [sys.executable, "-B", cli, action, "--project-root",
                 str(project), "--path", RECORD_REL, *args],
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True, text=True)

        def save(payload, token=inst.token):
            return run_cli("save", payload, "--runtime-root",
                           str(root / "runtime"), "--token", token)

        def restore():
            out = subprocess.run(
                [sys.executable, "-B", cli, "restore", "--module", "每日挑战",
                 "--records", str(records_dir)],
                capture_output=True, text=True)
            check(out.returncode == 0, f"CLI restore 应成功,实际 {out.stderr}")
            return json.loads(out.stdout)

        # 1) 正常保存:两题作答经通道落盘并回读
        reply = "Q1 选 B，Q2 选 A"
        rr = run_round(_turn(reply))
        out = save({"round_result": rr, "meta": _meta(reply=reply)})
        check(out.returncode == 0, f"CLI save 应成功,实际 {out.stderr}")
        applied = json.loads(out.stdout)
        check(applied["status"] == "saved" and applied["saved"] is True,
              f"CLI save 应经受控通道保存,实际 {applied['status']}")
        check((project / RECORD_REL).is_file(),
              "CLI 冒烟须留下实际保存记录作证")
        first_record = (project / RECORD_REL).read_text(encoding="utf-8")
        check("- D 每日挑战·Q1 关卡来源：采纳 B 每日生成新关" in first_record
              and "用户回复：「Q1 选 B，Q2 选 A」" in first_record,
              "实际记录须含本轮决定与用户回复")

        # 2) 部分回答:第三题保持未决并落盘
        partial_reply = "Q3 选 A"
        rr_partial = run_round(_turn(partial_reply, round_no=2,
                                     settled={"Q1": "B", "Q2": "A"},
                                     shown=["Q3"]))
        out = save({"round_result": rr_partial,
                    "meta": _meta(round_no=2, reply=partial_reply)})
        check(out.returncode == 0, f"部分回答保存应成功,实际 {out.stderr}")
        check("Q4 记录：依赖未满足" in (project / RECORD_REL).read_text(
            encoding="utf-8"), "未决项须落在实际记录中")

        # 3) 重复回答:同一作答不重复创建
        out = save({"round_result": rr, "meta": _meta(reply=reply)})
        check(out.returncode == 0, f"重复处理应可执行,实际 {out.stderr}")
        repeated = json.loads(out.stdout)
        check(repeated["status"] == "no_new" and repeated["saved"] is True,
              f"重复回答不得重复创建决定,实际 {repeated['status']}")
        after = (project / RECORD_REL).read_text(encoding="utf-8")
        check(after.count("·Q1 关卡来源：采纳") == 1,
              "重复处理后决定头仍只有一处")

        # 4) 改口:保留旧含义与替代关系
        revised_reply = "Q1 调整为 每日生成新关"
        rr_revised = run_round(_turn(revised_reply, round_no=3,
                                     settled={"Q1": "B", "Q2": "A", "Q3": "A"},
                                     shown=["Q4"]))
        out = save({"round_result": rr_revised,
                    "meta": _meta(round_no=3, reply=revised_reply)})
        check(out.returncode == 0, f"改口保存应成功,实际 {out.stderr}")
        revised_record = (project / RECORD_REL).read_text(encoding="utf-8")
        check("- D 每日挑战·Q1 关卡来源：采纳 B 每日生成新关（已被替代）"
              in revised_record, "改口须把旧决定标为已被替代")
        check("替代：「B 每日生成新关」（第 1 轮，历史保留）" in revised_record,
              "改口须留下替代关系")

        # 5) 中断恢复:从实际记录读已定与待同步
        state = restore()
        check(state["settled"]["Q1"] == "每日生成新关",
              f"恢复须读实际记录,实际 {state['settled']}")
        check(state["to_sync"] == ["Q1", "Q2", "Q3"],
              f"恢复须定位待同步内容,实际 {state['to_sync']}")
        check("待同步" in state["report"], "恢复报告须标明待同步")
        nxt = run_round(_turn("", settled=state["settled"]))
        check("Q1" not in nxt["shown_ids"] and "Q2" not in nxt["shown_ids"]
              and "Q3" not in nxt["shown_ids"], "已定决定不得重问")
        check(nxt["shown_ids"] == ["Q4"],
              f"恢复后只继续未完成部分,实际 {nxt['shown_ids']}")

        # 5b) 获准同步:标记为已同步后恢复只余真正待同步项
        unsynced_out = subprocess.run(
            [sys.executable, "-B", cli, "sync", "--project-root", str(project),
             "--path", RECORD_REL, "--runtime-root", str(root / "runtime"),
             "--token", inst.token, "--module", "每日挑战", "--qids", "Q1",
             "--sync-ref", "GAME_DESIGN v2", "--date", DATE],
            capture_output=True, text=True)
        check(unsynced_out.returncode == 1,
              f"未确认同步授权时不得标记已同步,实际 {unsynced_out.returncode}")
        check(json.loads(unsynced_out.stdout)["status"] == "unauthorized",
              "缺少同步授权时须保留待同步项")
        check((project / RECORD_REL).read_text(encoding="utf-8")
              == revised_record, "未授权同步不得改动记录")

        synced = subprocess.run(
            [sys.executable, "-B", cli, "sync", "--project-root", str(project),
             "--path", RECORD_REL, "--runtime-root", str(root / "runtime"),
             "--token", inst.token, "--module", "每日挑战", "--qids", "Q1",
             "--sync-ref", "GAME_DESIGN v2", "--date", DATE, "--authorized"],
            capture_output=True, text=True)
        check(synced.returncode == 0, f"CLI sync 应成功,实际 {synced.stderr}")
        synced_result = json.loads(synced.stdout)
        check(synced_result["status"] == "saved"
              and synced_result["synced"] == ["Q1"],
              f"同步标记须落盘并回读,实际 {synced_result['status']}")
        state_after_sync = restore()
        check(state_after_sync["to_sync"] == ["Q2", "Q3"],
              f"已同步项退出待同步,实际 {state_after_sync['to_sync']}")
        revised_record = (project / RECORD_REL).read_text(encoding="utf-8")

        # 6) 只读讨论:未授权时不写入且如实说明
        read_only = run_cli("plan", {
            "round_result": run_round(_turn("Q4 选 A", round_no=4,
                                            settled=state["settled"])),
            "meta": _meta(round_no=4, write=False, reply="Q4 选 A")})
        check(read_only.returncode == 0, f"只读计划应可执行,实际 {read_only.stderr}")
        read_plan = json.loads(read_only.stdout)
        check(read_plan["status"] == "read_only",
              f"未授权时应只读,实际 {read_plan['status']}")
        check("未保存" in read_plan["reason"] or "未获写入授权" in read_plan["reason"],
              "只读时须说明尚未保存")
        check((project / RECORD_REL).read_text(encoding="utf-8")
              == revised_record, "只读讨论不得改动实际记录")

        # 7) 失败:授权外凭据写入被受控通道拒绝,记录不变,报告真实状态
        limited = _instance(svc, resources=["docs/mygamestudio/GAME_DESIGN.md"])
        out = save({"round_result": run_round(
            _turn("Q4 选 A", round_no=4, settled=state["settled"])),
            "meta": _meta(round_no=4, reply="Q4 选 A")}, token=limited.token)
        check(out.returncode == 1, f"越界保存应以非零码报告失败,实际 {out.returncode}")
        denied = json.loads(out.stdout)
        check(denied["status"] == "denied"
              and denied["rule_stage"] == "task_grant"
              and denied["saved"] is False,
              f"越界写入须报告真实状态,实际 {denied}")
        check((project / RECORD_REL).read_text(encoding="utf-8")
              == revised_record, "被拒写入不得改动实际记录")

    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("decisions.py", "decision_records.py", "decisions_cli.py",
                   "plan_save", "apply_save", "plan_sync",
                   "restore_from_records", "回读", "待同步", "未保存"):
        check(needle in text, f"Game-Design 入口须说明 {needle}")


def _record(round_no, date, value, *, synced):
    status = (f"已同步（{date}，GAME_DESIGN v2）" if synced else "待同步")
    return (
        f"# 每日挑战：决定记录\n\n"
        f"## 第 {round_no} 轮 {date}\n"
        f"- 决定者：开发者。日期：{date}。\n"
        f"- 用户回复：「Q1 选 A」\n"
        f"- D 每日挑战·Q1 频率：采纳 {value}\n"
        f"  - 来源：开发者第 {round_no} 轮作答\n"
        f"  - 建议出处：Q1 推荐 A\n"
        f"  - 影响：决定挑战周期。\n"
        f"  - 同步状态：{status}\n")


def test_restore_merges_by_revision_not_filename() -> None:
    """跨记录恢复按决定身份与修订合并,同步状态不得串到新修订。"""

    older = _record(1, "2026-09-01", "每天一次", synced=True)
    newer = _record(2, "2026-09-14", "每周一次", synced=False)
    first = restore_from_records({
        "docs/z-round1.md": older, "docs/a-round2.md": newer}, "每日挑战")
    swapped = restore_from_records({
        "docs/a-round1.md": older, "docs/z-round2.md": newer}, "每日挑战")
    for state, label in ((first, "旧文件名靠后"), (swapped, "新文件名靠后")):
        check(state["settled"].get("Q1") == "每周一次",
              f"{label}应恢复较新修订,实际 {state['settled']}")
        check(state["decisions"]["Q1"]["synced"] is False,
              f"{label}新修订不得继承旧同步状态,实际 {state['decisions']}")
        check(state["to_sync"] == ["Q1"],
              f"{label}待同步须绑定新修订,实际 {state['to_sync']}")


def main() -> int:
    return run_theme("设计问答决定保存与恢复", (
        test_normal_save_matches_shown_questions_and_reads_back,
        test_partial_answer_records_open_items_and_reuses_module_record,
        test_repeated_same_answer_creates_no_duplicate,
        test_changed_decision_keeps_history_and_replacement,
        test_read_only_unsaved_and_restore_prevents_reasking,
        test_conflict_denied_and_unconfirmed_report_true_state,
        test_resume_after_interruption_keeps_valid_parts,
        test_states_do_not_conflate_saved_synced_implemented_verified,
        test_mcp_gate_tool_entry_saves_and_denies,
        test_cli_smoke_and_entry_points_to_seam,
        test_restore_merges_by_revision_not_filename,
    ), FAILURES)


if __name__ == "__main__":
    sys.exit(main())
