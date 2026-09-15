#!/usr/bin/env python3
"""统一设计问答框架票 08:减少重复读取与检查。

接缝:``plugin/skills/game-design/checks.py``——检查时机与复用接缝:内容身份与
指纹记录、会话内资料与检查结果的适用范围、复用判定与失效触发(外部修改引用
目标、撤销授权、版本冲突、写入失败、断链、证据不足)、每轮保存前/后核对范围、
模块收敛统一核对入口。接入票 03 决定保存(``decisions``)、票 04 模块规格交接
(``spec_draft``)、票 05 完整设计成稿(``full_design``)与票 06/07 变更/删减
(``change_flow``/``removal``):两条流程共用同一检查时机约定。

固定「齿轮谜城」场景分别经新设计与已有设计变更两条流程,用实际文件、受控通道
调用与检查台账证明:输入未变复用、每轮只做保存必需检查、收敛后一次统一核对、
外部改动/撤销授权/版本冲突/写入失败/断链后作废相关旧结果并只复查受影响部分;
受控通道的逐次权限与版本校验不被缓存跳过。期望值来自规格字面量与固定场景语义,
只经公共接口观察行为,不测内部函数。

    python3 -B tests/test_design_discussion_incremental_checks.py
"""

import json
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

from check_evidence import (  # noqa: E402
    evidence, ledger, measure, report, summary,
)
from checks import (  # noqa: E402
    after_save, begin, converge, invalidate, plan_reads, record_read,
    remember, reuse,
)
from decision_records import sha256_text  # noqa: E402
from decisions import apply_save, plan_save  # noqa: E402
from rounds import run_round  # noqa: E402
import change_flow  # noqa: E402
import full_design  # noqa: E402
import removal  # noqa: E402
import spec_draft  # noqa: E402

MODULE = "每日挑战"
RECORDS = "docs/mygamestudio/records"
RECORD_REL = f"{RECORDS}/decisions-每日挑战.md"
SPEC_REL = f"{RECORDS}/spec-每日挑战.md"
SPEC_OTHER_REL = f"{RECORDS}/spec-章节.md"
DESIGN_REL = "docs/mygamestudio/GAME_DESIGN.md"
PROJECT_REL = "docs/mygamestudio/PROJECT.md"
CONFIG_REL = "docs/mygamestudio/CONFIG.md"
DATE = "2026-09-14"

PROJECT_TEXT = "# 项目目标\n\n当前版本只做主线 20 关。\n"
CONFIG_TEXT = (
    "# 齿轮谜城:协作配置\n\n## 文档映射\n\n"
    f"| 内容 | 当前权威位置 |\n| --- | --- |\n"
    f"| 游戏需求与设计 | {DESIGN_REL} |\n"
    f"| 术语、ADR 与历史 | {RECORDS}/ |\n")
SPEC_TEXT = "# 每日挑战：模块规格\n\n## 正常规则\n- 每日一关。\n"
SPEC_OTHER_TEXT = "# 章节：模块规格\n\n## 正常规则\n- 章节按关卡顺序解锁。\n"
DESIGN_TEXT = (
    "# 齿轮谜城:当前游戏需求与设计\n\n基线版本:v2。\n\n"
    f"- 行为规则、边界、数值与验收：见模块规格 {SPEC_REL}。\n\n"
    "内容指纹：sha256:" + "0" * 64 + "\n"
    "归一指纹：sha256:" + "0" * 64 + "\n")


def _service(root: Path):
    """临时项目 + 真实受控通道服务(设计角色可写记录目录与核心基线)。"""

    project = root / "project"
    (project / "docs/mygamestudio/records").mkdir(parents=True)
    (project / DESIGN_REL).write_text(DESIGN_TEXT, encoding="utf-8")
    (project / PROJECT_REL).write_text(PROJECT_TEXT, encoding="utf-8")
    (project / CONFIG_REL).write_text(CONFIG_TEXT, encoding="utf-8")
    (project / SPEC_REL).write_text(SPEC_TEXT, encoding="utf-8")
    (project / SPEC_OTHER_REL).write_text(SPEC_OTHER_TEXT, encoding="utf-8")
    svc = GateService(root / "runtime")
    svc.init_policy(
        project_root=project,
        roles={"design": ["docs/mygamestudio/records/**", DESIGN_REL,
                          "docs/mygamestudio/CONTENT_PRODUCTION.md",
                          "docs/mygamestudio/VERSION_PLAN.md"]},
        purposes={
            "design_discussion": ["docs/mygamestudio/records/**"],
            "spec_sync": ["docs/mygamestudio/records/**", DESIGN_REL,
                          "docs/mygamestudio/CONTENT_PRODUCTION.md",
                          "docs/mygamestudio/VERSION_PLAN.md"],
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


def _questions():
    return [
        {"id": "Q1", "title": "关卡来源", "body": "每日关从哪来?",
         "options": {"A": "从现有 20 关按日期抽取", "B": "每日生成新关"},
         "recommendation": "A", "reason": "沿用现有内容最省制作。",
         "module": MODULE, "depends_on": [],
         "impact": "决定每日关的复用方式。"},
        {"id": "Q2", "title": "与章节关系", "body": "和章节什么关系?",
         "options": {"A": "独立于章节", "B": "并入章节"},
         "recommendation": "A", "reason": "保持章节主线独立。",
         "module": MODULE, "depends_on": [],
         "impact": "决定章节进度是否被每日挑战影响。"},
        {"id": "Q3", "title": "每日身份", "body": "为什么每天来?",
         "options": {"A": "连续参与奖励", "B": "无额外身份"},
         "recommendation": "A", "reason": "给回访一个理由。",
         "module": MODULE, "depends_on": [],
         "impact": "决定记录与奖励规则。"},
        {"id": "Q4", "title": "记录内容", "body": "记录哪些数据?",
         "options": {"A": "当日最佳", "B": "历史最佳"},
         "recommendation": "A", "reason": "只保存当日成绩最省。",
         "module": MODULE, "depends_on": ["Q3"],
         "impact": "决定存档键与验收。"},
    ]


def _turn(round_no, user_reply="", settled=None):
    return {
        "request": "设计每日挑战核心模块",
        "goal": "完成每日挑战核心模块",
        "module": MODULE,
        "round": round_no,
        "current_design": {"exists": True, "covers_request": False},
        "questions": _questions(),
        "settled": dict(settled or {}),
        "user_reply": user_reply,
    }


def _begin(project: Path, **overrides):
    context = {
        "mode": "new_design",
        "stage": "只有设计，尚未实现",
        "goal": "完成每日挑战核心模块",
        "module": MODULE,
        "deps": [],
        "entry": DESIGN_REL,
        "authorization": {"write": True, "sync": True},
        "baseline": {DESIGN_REL: sha256_text(DESIGN_TEXT)},
    }
    context.update(overrides)
    return begin(context)


def _candidates(project: Path):
    def sha(path: str) -> str:
        target = project / path
        return sha256_text(target.read_text(encoding="utf-8"))
    return [
        {"path": PROJECT_REL, "purpose": "project", "module": MODULE,
         "sha256": sha(PROJECT_REL), "mtime": 1},
        {"path": CONFIG_REL, "purpose": "rules", "module": MODULE,
         "sha256": sha(CONFIG_REL), "mtime": 1},
        {"path": SPEC_REL, "purpose": "module", "module": MODULE,
         "sha256": sha(SPEC_REL), "mtime": 1},
        {"path": SPEC_OTHER_REL, "purpose": "module", "module": "章节",
         "sha256": sha(SPEC_OTHER_REL), "mtime": 1},
    ]


def _load_batch(project: Path, session, out, call="本轮开始读取"):
    """按计划读取资料:一次调用内多个文件仍按文件分别记录。"""

    for item in out["to_read"]:
        result = record_read(session, item["path"],
                             (project / item["path"]).read_text(encoding="utf-8"),
                             module=MODULE, purpose=item["purpose"], call=call)
        session = result["session"]
    return session


def _paths(items):
    return [item["path"] for item in items]


def _entries(entries, needle):
    return [item for item in entries if needle in str(item.get("check") or "")]


def test_read_plan_reuses_unchanged_and_excludes_unrelated() -> None:
    """开始/恢复只展开当前模块与必要依赖;输入未变复用,无关模块不读。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        out = _begin(project)
        session = out["session"]
        check(out["ok"] is True, f"开始核对应通过,实际缺口:{out['gaps']}")
        check(session["mode"] == "new_design" and session["module"] == MODULE,
              "会话应记录模式与当前模块")
        check(session["entry"] == DESIGN_REL, "应从现有入口定位资料")

        plan = plan_reads(session, _candidates(project))
        check(_paths(plan["to_read"])
              == [PROJECT_REL, CONFIG_REL, SPEC_REL],
              f"首轮应读取当前模块与必要资料,实际 {_paths(plan['to_read'])}")
        check(_paths(plan["excluded"]) == [SPEC_OTHER_REL],
              f"无关模块资料不应展开,实际 {_paths(plan['excluded'])}")
        session = _load_batch(project, session, plan)
        ev = evidence(session)
        check(ev["calls"] == 1 and ev["reads"]["file_ops"] == 3,
              f"一次调用内 3 个文件应分别计数,实际 {ev['reads']}/{ev['calls']}")

        again = plan_reads(session, _candidates(project))
        check(again["to_read"] == [], "输入未变时不应重读已读资料")
        check(_paths(again["reuse"])
              == [PROJECT_REL, CONFIG_REL, SPEC_REL],
              f"已读且未变资料应复用,实际 {_paths(again['reuse'])}")
        check(_paths(again["excluded"]) == [SPEC_OTHER_REL],
              "无关模块仍不展开")
        # 只改修改时间、内容未变:复用;内容变了才重读。
        touched = _candidates(project)
        for item in touched:
            item["mtime"] = 99
        check(plan_reads(session, touched)["to_read"] == [],
              "不能仅凭修改时间判断有效;内容指纹未变应复用")
        changed = _candidates(project)
        for item in changed:
            if item["path"] == SPEC_REL:
                item["sha256"] = sha256_text(SPEC_TEXT + "-改")
        plan2 = plan_reads(session, changed)
        check(_paths(plan2["to_read"]) == [SPEC_REL],
              f"内容变化只重读受影响资料,实际 {_paths(plan2['to_read'])}")
        check(_paths(plan2["reuse"]) == [PROJECT_REL, CONFIG_REL],
              "其余资料继续复用")
        # 新会话只能用可核验身份复用:无记录来源的候选一律补读。
        out3 = _begin(project)
        session3 = out3["session"]
        seed = {"path": DESIGN_REL, "purpose": "baseline", "module": MODULE,
                "sha256": sha256_text(DESIGN_TEXT)}
        plan3 = plan_reads(session3, [seed])
        check(_paths(plan3["to_read"]) == [DESIGN_REL],
              "新会话没有可核验身份时应补做读取")


def test_round_save_checks_before_and_after_without_global_rerun() -> None:
    """每轮保存前后都有核对;输入未变复用;不因新增决定重跑全局检查。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project)["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        instance = _instance(svc)
        channel = _Channel(svc, instance.token)
        answers = ("Q1 选 A", "Q2 选 A", "Q3 选 A")
        settled: dict = {}

        for round_no, answer in enumerate(answers, start=1):
            result = run_round(_turn(round_no, answer, settled=settled))
            meta = {"record_path": RECORD_REL, "module": MODULE,
                    "round": round_no, "date": DATE,
                    "authorization": {"write": True, "sync": False}}
            plan = plan_save(read(RECORD_REL), result, meta, session=session)
            check(plan.get("checks_ok") is True,
                  f"第 {round_no} 轮保存前核对应通过:{plan.get('checks')}")
            check(plan.get("checks", {}).get("timing") == "before_save",
                  "保存前核对应记录时机")
            saved = apply_save(plan, channel, read, session=plan["session"])
            check(saved.get("saved") is True,
                  f"第 {round_no} 轮应经通道保存:{saved.get('report')}")
            check(saved.get("checks", {}).get("timing") == "after_save",
                  "保存后核对应记录时机")
            check(saved["checks"]["ok"] is True,
                  f"第 {round_no} 轮保存后核对应通过:{saved['checks']}")
            session = saved["session"]
            for qid, item in result["adopted"].items():
                settled[str(qid)] = item["value"]

        check(len(channel.scopes) == len(answers),
              f"逐次写入校验不得缓存跳过:每次写入都应核对范围,"
              f"实际 {len(channel.scopes)}")
        check(len(channel.writes) == len(answers), "三轮各写入一次记录")
        pre = ledger(session, timing="before_save")
        post = ledger(session, timing="after_save")
        check(len(pre) >= 3 and len(post) >= 3, "每轮都有保存前后核对")
        skipped = [item for item in post
                   if item.get("status") == "skipped"
                   and "全局" in str(item.get("check") or "")]
        check(len(skipped) >= 3,
              f"未改核心基线时不应重跑全项目基线/全部链接/远端检查:{post}")
        check(not _entries(session["results"], "全项目基线"),
              "不得在连续轮次里执行全项目基线检查")
        ev = evidence(session)
        check(ev["reads"]["file_ops"] == 3, f"三轮只读取一次资料:{ev['reads']}")
        check(ev["writes"]["file_ops"] == 3, f"三轮各写一次:{ev['writes']}")
        # 本模块记录经实际写入后身份已知:下一轮不重读,资料继续复用。
        candidates = _candidates(project) + [
            {"path": RECORD_REL, "purpose": "记录", "module": MODULE,
             "sha256": sha256_text(read(RECORD_REL))}]
        again = plan_reads(session, candidates)
        check(again["to_read"] == [],
              f"写入后的记录身份已知,下一轮不重读:{again['to_read']}")
        check(RECORD_REL in _paths(again["reuse"]),
              "写入后的记录应进入复用集合")


def test_precheck_gap_blocks_save_without_disk_checks() -> None:
    """保存前核对发现采纳超范围时,不得进入写入与落盘检查。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project)["session"]
        instance = _instance(svc)
        channel = _Channel(svc, instance.token)
        result = run_round(_turn(1, "Q1 选 A"))
        result["adopted"]["Q9"] = {"value": "X", "source": "user"}
        plan = plan_save(read(RECORD_REL), result,
                         {"record_path": RECORD_REL, "module": MODULE,
                          "round": 1, "date": DATE,
                          "authorization": {"write": True, "sync": False}},
                         session=session)
        check(plan.get("checks_ok") is False, "采纳超范围应判为保存前缺口")
        gaps = plan.get("checks", {}).get("gaps") or []
        check(any("Q9" in str(item) for item in gaps),
              f"缺口应指出超范围问题:{gaps}")
        blocked = apply_save(plan, channel, read, session=session)
        check(blocked.get("saved") is False and not channel.writes,
              "保存前检查未通过时不得写入")
        check(channel.scopes == [], "未写入时不应运行落盘范围检查")
        check(not (project / RECORD_REL).exists(), "记录不应被半写")


def test_invalidation_only_drops_affected_parts() -> None:
    """外部修改/断链/证据不足时只作废受影响部分,无关模块不被全量重查。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        session = _begin(project)["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        # 此前轮次到过的其他模块资料:读取结果保留,不被局部失败波及。
        session = record_read(session, SPEC_OTHER_REL, SPEC_OTHER_TEXT,
                              module="章节", purpose="module",
                              call="上一模块读取")["session"]
        remembered = remember(session, "规格完整性", {"ok": True},
                              depends_on=[SPEC_REL])["session"]
        other = remember(remembered, "章节链接", {"ok": True},
                         depends_on=[SPEC_OTHER_REL])["session"]
        out = invalidate(other, "external_change", paths=[SPEC_REL])
        session = out["session"]
        check(out["stale"] == [SPEC_REL],
              f"只作废被改目标的旧读取,实际 {out['stale']}")
        check(SPEC_OTHER_REL in session["reads"],
              "无关模块的读取结果应保留")
        check(reuse(session, "章节链接") is not None,
              "无关模块的已通过检查仍可复用")
        check(reuse(session, "规格完整性") is None,
              "受影响目标的旧检查结果应作废")
        plan = plan_reads(session, _candidates(project))
        check(_paths(plan["to_read"]) == [SPEC_REL],
              f"只重读受影响资料,实际 {_paths(plan['to_read'])}")
        check(_paths(plan["reuse"]) == [PROJECT_REL, CONFIG_REL],
              "无关资料继续复用")
        broken = invalidate(session, "broken_link", paths=[PROJECT_REL])
        check(broken["label"] == "断链" and broken["stale"] == [PROJECT_REL],
              f"断链应按名称记录并只作废断链目标:{broken}")
        weak = invalidate(session, "insufficient_evidence", paths=[])
        check(weak["stale"] == [] and "证据不足" in weak["report"],
              f"证据不足应如实记录:{weak}")


def test_revoked_authorization_rechecks_only_affected() -> None:
    """授权撤销后旧检查结果失效;重新授权只补受影响检查。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project)["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        session = record_read(session, SPEC_OTHER_REL, SPEC_OTHER_TEXT,
                              module="章节", purpose="module",
                              call="上一模块读取")["session"]
        session = remember(session, "记录完整性", {"ok": True},
                           depends_on=[RECORD_REL])["session"]
        instance = _instance(svc)
        channel = _Channel(svc, instance.token)
        result = run_round(_turn(1, "Q1 选 A"))
        meta = {"record_path": RECORD_REL, "module": MODULE, "round": 1,
                "date": DATE, "authorization": {"write": True, "sync": False}}
        plan = plan_save(read(RECORD_REL), result, meta, session=session)
        saved = apply_save(plan, channel, read, session=plan["session"])
        check(saved["saved"] is True, "首次保存应成功")
        session = saved["session"]
        scopes_before = len(channel.scopes)

        svc.release_instance(instance.instance_id)
        result2 = run_round(_turn(2, "Q2 选 A", settled={"Q1": "A"}))
        plan2 = plan_save(read(RECORD_REL), result2,
                          {**meta, "round": 2}, session=session)
        denied = apply_save(plan2, channel, read, session=plan2["session"])
        check(denied["saved"] is False,
              "授权撤销后不得再写成功")
        check(len(channel.scopes) > scopes_before,
              "撤销后仍须逐次走通道核对,不得用缓存跳过")
        check(denied.get("checks", {}).get("timing") == "before_save",
              "被拒时保留保存前核对结果")
        session = denied["session"]
        check(session["authorization"].get("write") is False,
              "撤销后会话授权应更新为不可写")
        check(reuse(session, "记录完整性") is None,
              "撤销授权后旧的可复用检查结果作废")
        check(SPEC_OTHER_REL in session["reads"],
              "无关模块读取结果保留,不因局部失败全量重查")

        # 重新签发凭据后:只补受影响检查,未变资料继续复用。
        again = _instance(svc)
        channel2 = _Channel(svc, again.token)
        plan3 = plan_save(read(RECORD_REL), result2,
                          {**meta, "round": 2}, session=session)
        check(plan3["checks_ok"] is True,
              f"重新授权后保存前核对应通过:{plan3.get('checks')}")
        saved3 = apply_save(plan3, channel2, read, session=plan3["session"])
        check(saved3["saved"] is True, f"重新授权后应可保存:{saved3}")


def test_conflict_and_write_failure_invalidate_target() -> None:
    """版本冲突与写入失败作废受影响结果,只重读记录本身。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project)["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        session = record_read(session, SPEC_OTHER_REL, SPEC_OTHER_TEXT,
                              module="章节", purpose="module",
                              call="上一模块读取")["session"]
        session = remember(session, "记录完整性", {"ok": True},
                           depends_on=[RECORD_REL])["session"]
        instance = _instance(svc)
        channel = _Channel(svc, instance.token)
        result = run_round(_turn(1, "Q1 选 A"))
        meta = {"record_path": RECORD_REL, "module": MODULE, "round": 1,
                "date": DATE, "authorization": {"write": True, "sync": False}}
        plan = plan_save(read(RECORD_REL), result, meta, session=session)
        # 外部先写入同一记录:计划的目标版本过期。
        external = "# 每日挑战：决定记录\n\n## 第 1 轮 2026-09-13\n"
        (project / RECORD_REL).write_text(external, encoding="utf-8")
        conflicted = apply_save(plan, channel, read, session=plan["session"])
        check(conflicted["status"] == "conflict",
              f"外部修改应报版本冲突:{conflicted.get('status')}")
        check(not channel.writes, "冲突时不得写入")
        session = conflicted["session"]
        check(session.get("target_version") is None,
              "冲突后目标版本缓存应作废")
        check(reuse(session, "记录完整性") is None,
              "冲突后受影响记录的旧检查结果作废")
        candidates = _candidates(project) + [
            {"path": RECORD_REL, "purpose": "记录", "module": MODULE,
             "sha256": sha256_text(external)}]
        plan2 = plan_reads(session, candidates)
        check(_paths(plan2["to_read"]) == [RECORD_REL],
              f"冲突后只重读受影响记录:{_paths(plan2['to_read'])}")
        check(_paths(plan2["reuse"]) == [PROJECT_REL, CONFIG_REL, SPEC_REL],
              "无关资料继续复用")

        # 写入失败(回读不确认)同样作废目标并如实报告。
        plan3 = plan_save(read(RECORD_REL), result,
                          {**meta, "round": 2}, session=plan2["session"])
        plan3["session"] = remember(
            plan3["session"], "记录完整性", {"ok": True},
            depends_on=[RECORD_REL])["session"]
        failing = _FailingReader(read)
        failing.fail_path = RECORD_REL
        lost = apply_save(plan3, channel, failing,
                          session=plan3["session"])
        check(lost["status"] == "save_unconfirmed",
              f"回读失败不得称已保存:{lost.get('status')}")
        check(lost["session"].get("target_version") is None,
              "写入失败后目标版本缓存作废")
        check(reuse(lost["session"], "记录完整性") is None,
              "写入失败后相关旧结果作废")
        check(SPEC_OTHER_REL in lost["session"]["reads"],
              "无关模块读取结果保留")


def test_converge_runs_once_with_real_scope() -> None:
    """模块收敛后按真实影响做一次统一核对;跨模块才扩大范围。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        session = _begin(project)["session"]
        record = (
            "# 每日挑战：决定记录\n\n## 第 1 轮 2026-09-14\n"
            "- 决定者：开发者。日期：2026-09-14。\n"
            "- D 每日挑战·Q1 关卡来源：采纳 A 从现有 20 关抽取\n"
            "  - 来源：开发者逐题选择\n  - 同步状态：待同步\n")
        local = converge(session, {"module": MODULE, "records":
                                   {RECORD_REL: record}})
        check(local["to_sync"] == ["Q1"], f"应汇总未同步决定:{local}")
        check(local["scope"] == "当前模块",
              f"无跨模块影响时只核对当前模块:{local['scope']}")
        entries = ledger(local["session"], timing="converge")
        check(len(entries) == 1 and "未同步决定" in entries[0]["check"],
              f"收敛只做一次统一核对:{entries}")
        cross = converge(local["session"], {
            "module": MODULE, "records": {RECORD_REL: record},
            "impact": {"must_sync": [{"id": "daily_reward",
                                      "module": "成长资源"}]},
            "files": [{"path": SPEC_REL}, {"path": DESIGN_REL}]})
        check(cross["scope"] == "跨模块",
              f"确有跨模块影响才扩大范围:{cross['scope']}")
        check(set(cross["affected"]) == {SPEC_REL, DESIGN_REL},
              f"受影响范围应可定位:{cross['affected']}")


def test_report_keeps_save_result_and_short_details() -> None:
    """日常回复只保留保存结果与简要限制,检查明细留在台账。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project)["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        instance = _instance(svc)
        channel = _Channel(svc, instance.token)
        result = run_round(_turn(1, "Q1 选 A"))
        meta = {"record_path": RECORD_REL, "module": MODULE, "round": 1,
                "date": DATE, "authorization": {"write": True, "sync": False}}
        plan = plan_save(read(RECORD_REL), result, meta, session=session)
        saved = apply_save(plan, channel, read, session=plan["session"])
        line = report(saved["session"], {"op": "save", **saved})
        check("已保存" in line and "检查" in line,
              f"回复应保留保存结果与检查数:{line}")
        check("\n" not in line, "日常回复只保留一句摘要")
        detail = summary(saved["session"])
        check("保存前核对" in detail and "保存后回读" in detail,
              f"检查明细在台账中简短保留:{detail}")
        read_only = plan_save(read(RECORD_REL), run_round(_turn(2, "Q2 选 A")),
                              {**meta, "round": 2,
                               "authorization": {"write": False}},
                              session=saved["session"])
        check(read_only["status"] == "read_only",
              "纯讨论未授权时应保持只读")
        check(read_only["saved"] is False, "只读不得声称已保存")
        check(len(channel.writes) == 1, "只读轮次不得新增写入")
        read_only_result = apply_save(read_only, channel, read,
                                      session=read_only["session"])
        check(read_only_result["session"]["authorization"]["write"] is False,
              "只读不改变会话的只读状态")
        # 重复答案(no_new):本轮没有新增内容时不得作废任何旧结果。
        before = _load_batch(project, saved["session"],
                             plan_reads(saved["session"],
                                        _candidates(project)))
        again = plan_save(read(RECORD_REL),
                          run_round(_turn(2, "Q1 选 A",
                                          settled={"Q1": "A"})),
                          {**meta, "round": 2}, session=before)
        check(again["status"] == "no_new",
              f"重复答案应为 no_new:{again.get('status')}")
        no_new = apply_save(again, channel, read, session=again["session"])
        check(no_new["session"]["reads"] == before["reads"],
              "no_new 不得作废既有读取结果")
        check(no_new["session"].get("target_version")
              == before.get("target_version"),
              "no_new 不得作废目标版本")


def test_full_design_delivery_reuses_reads_and_records_writes() -> None:
    """新设计成稿接入同一检查时机:未变复用、写入按文件计数、收敛一次核对。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        (project / "docs/mygamestudio/CONTENT_PRODUCTION.md").write_text(
            "# 内容\n\n既有说明：音效沿用现有素材。\n", encoding="utf-8")
        session = _begin(project, mode="new_design")["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        instance = _instance(
            svc, purpose="spec_sync",
            resources=["docs/mygamestudio/records/**", DESIGN_REL,
                       "docs/mygamestudio/CONTENT_PRODUCTION.md",
                       "docs/mygamestudio/VERSION_PLAN.md"])
        channel = _Channel(svc, instance.token)
        plan = full_design.plan_delivery(_existing_for(read, _delivery_meta()),
                                         _delivery_meta(),
                                         _delivery_material())
        check(plan["status"] == "planned",
              f"完整交付应可计划:{plan.get('status')}:{plan.get('missing')}")
        saved = full_design.apply_delivery(plan, channel, read,
                                          session=session)
        check(saved.get("saved") is True, f"交付应经通道写入:{saved}")
        session = saved["session"]
        ev = evidence(session)
        check(ev["writes"]["file_ops"] == len(plan["files"]),
              f"按文件计数写入,实际 {ev['writes']}")
        check(len(channel.writes) == len(plan["files"]),
              "每个文件都逐次经通道校验,不合并跳过")
        check(ledger(session, timing="converge"),
              "成稿落盘前应做一次收敛统一核对")
        again = plan_reads(session, _candidates(project))
        check(again["to_read"] == [],
              f"输入未变的复跑不重读资料:{again['to_read']}")


def test_change_flow_reuses_reads_and_records_writes() -> None:
    """已有设计变更接入同一检查时机:未变复用、写入按文件计数、收敛一次核对。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project, mode="design_change")["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        instance = _instance(svc, purpose="spec_sync",
                             resources=["docs/mygamestudio/records/**",
                                        DESIGN_REL])
        channel = _Channel(svc, instance.token)
        change_meta = {
            "module": MODULE, "date": DATE,
            "design_path": DESIGN_REL,
            "change_record_path": f"{RECORDS}/change-每日挑战.md",
            "version_from": "v2", "version_to": "v3",
            "authorization": {"write": True, "sync": True},
        }
        existing = {SPEC_REL: read(SPEC_REL), DESIGN_REL: read(DESIGN_REL)}
        plan = change_flow.plan_change(existing, change_meta,
                                       _change_material())
        check(plan["status"] == "planned",
              f"变更应可计划:{plan.get('status')}:{plan.get('unresolved')}")
        saved = change_flow.apply_change(plan, channel, read,
                                        session=session)
        check(saved.get("saved") is True, f"变更应经通道写入:{saved}")
        session = saved["session"]
        ev = evidence(session)
        check(ev["writes"]["file_ops"] == len(plan["files"]),
              f"按文件计数写入,实际 {ev['writes']}")
        check(len(channel.writes) == len(plan["files"]),
              "每个文件都逐次经通道校验,不合并跳过")
        check(ledger(session, timing="converge"),
              "同步前应做一次收敛统一核对")
        again = plan_reads(session, _candidates(project))
        check(again["to_read"] == [],
              f"输入未变的复跑不重读资料:{again['to_read']}")


class _FailingReader:
    """回读失败注入:版本核对读得到,写入后的回读返回 None。"""

    def __init__(self, read):
        self.read = read
        self.seen = {}
        self.fail_path = None

    def __call__(self, path):
        if path == self.fail_path:
            self.seen[path] = self.seen.get(path, 0) + 1
            if self.seen[path] > 1:
                return None
        return self.read(path)


def _delivery_material():
    """新设计成稿材料:十二领域、流程、边界与规则齐备,可交接。"""

    domains = {
        "project": {"applies": True, "rules": PROJECT_REL},
        "appeal": {"applies": True, "rules": f"{DESIGN_REL}（核心体验）"},
        "core_play": {"applies": True, "rules": SPEC_REL},
        "journey": {"applies": True, "rules": f"{DESIGN_REL}（完整流程）"},
        "systems": {"applies": True, "rules": SPEC_REL},
        "growth": {"applies": True, "rules": f"{SPEC_REL}（数值与配置）"},
        "content": {"applies": True, "rules": SPEC_REL},
        "ui": {"applies": True, "rules": f"{DESIGN_REL}（界面与引导）"},
        "presentation": {"applies": True, "rules": "CONTENT_PRODUCTION.md"},
        "release": {"applies": False, "reason": "本作只做本地游玩,不上架"},
        "tech": {"applies": "unknown", "method": "读取 TECH_DESIGN.md 核对存档",
                 "impact": "决定存档兼容"},
        "version": {"applies": True, "rules": SPEC_REL},
    }
    return {
        "known": {"gameplay": ["推箱开门"], "visuals": ["齿轮风格"],
                  "operations": ["方向键推箱"], "feelings": ["短局解谜"],
                  "references": ["参考经典推箱子"]},
        "experience": [
            {"text": "进入关卡推齿轮开门", "source": "intent"},
            {"text": "每日挑战复用现有 20 关", "source": "intent"},
            {"text": "结算给出步数评价", "source": "proposal"},
        ],
        "scope": {
            "vision": ["联机对战"],
            "current": [{"text": "每日挑战本机模式", "source": "decision"}],
            "later": ["每日排行榜"],
            "out_of_scope": ["付费商店"],
            "clarify": [],
        },
        "domains": domains,
        "journey": {
            "first_entry": {"status": "closed", "detail": "主菜单进入"},
            "understand_goal": {"status": "closed", "detail": "入口显示日期"},
            "operate": {"status": "closed", "detail": "推箱操作"},
            "choose": {"status": "closed", "detail": "选择推动方向"},
            "result": {"status": "closed", "detail": "结算显示步数"},
            "end": {"status": "closed", "detail": "完成或退出回主菜单"},
            "reenter": {"status": "closed", "detail": "再次进入读当日最佳"},
        },
        "checks": {
            "resource_exhaustion": {"applies": True, "detail": "步数无上限"},
            "repeat": {"applies": True, "detail": "同日只保留更优成绩"},
            "exit": {"applies": True, "detail": "中途退出不记录最佳"},
            "unlock": {"applies": True, "detail": "每日挑战需齿轮币解锁"},
            "failure_recovery": {"applies": False, "reason": "无失败状态"},
        },
        "economy": {"sources": [{"id": "daily_reward", "amount": 3}],
                    "requirements": [{"id": "unlock", "amount": 3}],
                    "note": "收支一致"},
        "design": {
            "overview": "章节式推箱解谜,新增每日挑战本机模式。",
            "core_experience": "短局解谜与每日回来的理由。",
            "core_loop": "进入关卡 → 推箱 → 开门 → 结算。",
            "system_relations": f"每日挑战引用章节关卡规则;见 {SPEC_REL}。",
        },
        "content": {
            "levels_events": [{"text": "每日一关", "rules": ["R1"]}],
            "templates": [{"text": "复用章节关卡模板", "rules": []}],
            "characters": [{"text": "无新角色", "rules": []}],
            "scenes": [{"text": "沿用齿轮场景", "rules": []}],
            "ui": [{"text": "主菜单增加每日挑战入口", "rules": []}],
            "animation_vfx": [{"text": "沿用既有表现", "rules": []}],
            "audio": [{"text": "沿用现有音效", "rules": ["R1"]}],
        },
        "rules": [{"id": "R1", "title": "每日种子规则",
                   "location": SPEC_REL, "text": "本机日历日加固定种子"}],
        "prototype": [{"question": "每日一局是否有重复游玩动力",
                       "goal": "确认长期吸引力",
                       "method": "原型连续 3 天试玩并记录完成率",
                       "judgement": "完成率不低于 60%",
                       "blocks_stage": False}],
        "acceptance": [{"initial": "新档,当日未玩",
                        "action": "从主菜单进入每日挑战并完成一局",
                        "expected": "记录当日最佳步数,再次进入可读"}],
        "risks": ["联网排行榜当前无联网能力"],
        "dependencies": ["沿用现有 20 关内容与既有存档"],
        "existing": {"materials": [{"path": PROJECT_REL}, {"path": SPEC_REL}],
                     "decisions": [{"qid": "Q1", "value": "A 从现有 20 关抽取"}]},
        "stage_evidence": {
            "concept": {"required": ["核心吸引力明确"],
                        "met": ["核心吸引力明确"]},
            "prototype_spec": {"required": ["核心规则可执行"],
                               "met": ["核心规则可执行"]},
            "current_version": {
                "required": ["十二领域覆盖无阻断缺口", "关键流程闭合",
                             "必要模块规格可交接"],
                "met": ["十二领域覆盖无阻断缺口", "关键流程闭合",
                        "必要模块规格可交接"]},
        },
    }


def _delivery_meta():
    return {
        "game": "齿轮谜城", "date": DATE,
        "version_from": "v2", "version_to": "v3",
        "doc_map": {"design": DESIGN_REL,
                    "content": "docs/mygamestudio/CONTENT_PRODUCTION.md",
                    "version": "docs/mygamestudio/VERSION_PLAN.md"},
        "module_specs": [{"module": MODULE, "spec_path": SPEC_REL,
                          "status": "handoffable", "gaps": []}],
        "necessary_modules": [MODULE],
        "authorization": {"write": True, "sync": True},
        "untouched": [PROJECT_REL],
    }


def _existing_for(read, meta: dict) -> dict:
    """本次将写入的实际内容:写入前按实际回读核对目标版本。"""

    doc_map = dict(meta.get("doc_map") or {})
    paths = [str(doc_map.get(key) or "") for key in ("design", "content",
                                                     "version")]
    for item in meta.get("module_specs") or []:
        paths.append(str(item.get("spec_path") or ""))
    return {path: read(path) for path in paths if path}


def _change_material():
    design_items = [
        {"id": "loop", "module": MODULE, "lane": "rules",
         "title": "每日循环", "location": SPEC_REL,
         "old_text": "- 每日一关。", "new_text": "- 每日一关,当日结算一次。"},
    ]
    return {
        "request": {"state": "decided", "text": "把每日循环写清"},
        "change": {"targets": ["loop"], "target_labels": ["每日循环"],
                   "reason": "规则不清", "improvement": "明确结算",
                   "keep": ["20 关内容"], "answers": []},
        "stage": "design_only",
        "stage_basis": "只有设计，尚未实现",
        "objects": {
            "rules": {"exists": True, "evidence": "模块规格已有独立规则"},
            "flow": {"exists": True, "evidence": "流程已写清"},
            "numbers": {"exists": True, "evidence": "数值已给出"},
            "content_list": {"exists": True, "evidence": "内容清单已有"},
            "acceptance": {"exists": True, "evidence": "验收已写"},
        },
        "design_items": design_items,
        "impact": {
            "must_sync": [{"id": "loop", "title": "每日循环", "relation": "direct",
                           "old_text": "- 每日一关。",
                           "new_text": "- 每日一关,当日结算一次。",
                           "location": SPEC_REL}],
            "needs_tradeoff": [], "unaffected": [], "unresolved": [],
        },
        "candidates": [], "walkthrough": [], "results": [],
        "modules": [{"id": MODULE, "title": "每日挑战"}],
    }



def test_spec_handoff_and_removal_share_timing() -> None:
    """模块规格交接与功能删减接入同一检查时机:收敛一次核对、按文件计数。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project)["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        record = (
            "# 每日挑战：决定记录\n\n## 第 1 轮 2026-09-14\n"
            "- 决定者：开发者。日期：2026-09-14。\n"
            "- D 每日挑战·Q1 关卡来源：采纳 A 从现有 20 关按日期抽取\n"
            "  - 来源：开发者逐题选择\n  - 同步状态：待同步\n")
        (project / RECORD_REL).write_text(record, encoding="utf-8")
        instance = _instance(
            svc, purpose="spec_sync",
            resources=["docs/mygamestudio/records/**", DESIGN_REL,
                       "docs/mygamestudio/glossary.md"])
        channel = _Channel(svc, instance.token)
        meta = {
            "module": MODULE, "date": DATE, "record_path": RECORD_REL,
            "spec_path": SPEC_REL, "design_path": DESIGN_REL,
            "glossary_path": "docs/mygamestudio/glossary.md",
            "sync_ref": "GAME_DESIGN v3",
            "version_from": "v2", "version_to": "v3",
            "change": "substantive",
            "authorization": {"write": True, "sync": True},
            "sections": _handoff_sections(), "glossary": [], "adr": [],
            "scope_change": [], "verification": [], "proposals": [],
            "assumptions": [], "blocking_qids": [],
            "untouched": [PROJECT_REL],
        }
        existing = {SPEC_REL: read(SPEC_REL), DESIGN_REL: read(DESIGN_REL),
                    "docs/mygamestudio/glossary.md":
                        read("docs/mygamestudio/glossary.md")}
        plan = spec_draft.plan_handoff({RECORD_REL: record}, meta, existing)
        check(plan["status"] == "planned",
              f"收敛模块应可交接:{plan.get('status')}:{plan.get('missing')}")
        applied = spec_draft.apply_handoff(plan, channel, read,
                                           session=session)
        check(applied.get("saved") is True,
              f"交接应经通道写入:{applied.get('status')}")
        check(ledger(applied["session"], timing="converge"),
              "模块收敛交接前应做一次统一核对")
        ev = evidence(applied["session"])
        check(ev["writes"]["file_ops"] == len(plan["files"]),
              f"交接按文件计数写入,实际 {ev['writes']}")
        check(len(channel.writes) == len(plan["files"]),
              "每个交接文件都逐次经通道校验")

        removal_plan = change_flow.plan_change(
            {SPEC_REL: read(SPEC_REL), DESIGN_REL: read(DESIGN_REL)},
            {"module": MODULE, "date": DATE, "design_path": DESIGN_REL,
             "change_record_path": f"{RECORDS}/change-删减.md",
             "version_from": "v3", "version_to": "v4",
             "authorization": {"write": True, "sync": True}},
            _change_material())
        if removal_plan["status"] != "planned":
            check("旧规则未定位" in json.dumps(removal_plan["unresolved"],
                                              ensure_ascii=False),
                  f"删减计划只应因旧规则已被前一步改写而暂缺:{removal_plan['status']}")
        else:
            applied_removal = removal.apply_removal(
                removal_plan, channel, read,
                session=applied["session"])
            check(applied_removal.get("op") == "removal"
                  and applied_removal.get("saved") is True,
                  f"删减应沿用同一受控通道与检查时机:{applied_removal}")


def test_measure_counts_actual_events() -> None:
    """固定场景的实际读取、写入、检查与调用依据:调用内多文件分别计数。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project)["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        instance = _instance(svc)
        channel = _Channel(svc, instance.token)
        settled: dict = {}
        for round_no, answer in enumerate(("Q1 选 A", "Q2 选 A", "Q3 选 A"),
                                          start=1):
            result = run_round(_turn(round_no, answer, settled=settled))
            plan = plan_save(read(RECORD_REL), result,
                             {"record_path": RECORD_REL, "module": MODULE,
                              "round": round_no, "date": DATE,
                              "authorization": {"write": True, "sync": False}},
                             session=session)
            saved = apply_save(plan, channel, read, session=plan["session"])
            session = saved["session"]
            for qid, item in result["adopted"].items():
                settled[str(qid)] = item["value"]
        stats = measure(session, module=MODULE)
        check(stats["reads"]["file_ops"] == 3,
              f"三轮只读取一次资料(3 个文件):{stats['reads']}")
        check(stats["reads"]["calls"] == 1,
              f"同一次调用内的 3 个文件仍分别计数:{stats['reads']}")
        check(stats["writes"]["file_ops"] == 3,
              f"三轮各写一次记录:{stats['writes']}")
        check(stats["rounds"] == 3, f"三轮都有保存后核对:{stats['rounds']}")
        check(stats["checks"] >= 6, f"每轮保存前后核对:{stats['checks']}")
        check(stats["calls"] >= 4, f"调用计数按实际事件:{stats['calls']}")


def test_game_design_entry_points_to_checks_seam() -> None:
    """Game-Design 入口说明检查时机与复用接缝,不新增公共入口。"""

    text = LEGACY_DESIGN_ENTRY.read_text(encoding="utf-8")
    for needle in ("checks.py", "begin", "plan_reads", "before_save",
                   "after_save", "converge", "invalidate"):
        check(needle in text, f"入口应指向 {needle}")
    for concept in ("检查时机", "复用", "内容指纹", "修改时间",
                    "逐次", "缓存", "全项目基线", "全量", "断链",
                    "无关模块", "纯讨论", "不新增独立缓存服务",
                    "不新建公共入口"):
        check(concept in text, f"入口应覆盖概念:{concept}")


def _handoff_sections():
    """交接夹具的九类规格内容:可判定规则与数值,不适用写出理由。"""

    return {
        "purpose": {"content": "让玩家每天用一次短局回到游戏;复用已有关卡。",
                    "sources": ["Q1"]},
        "participants": {"content": "主菜单入口、当日关卡、当日最佳步数记录。",
                    "sources": ["Q1"]},
        "triggers": {"content": "玩家从主菜单进入每日挑战时生效;"
                                "当日关卡按本机日期从现有 20 关选择。",
                     "sources": ["Q1"]},
        "rules": {"content": "选择当日关卡 → 完成一局 → 按步数结算 → "
                             "更新当日最佳;每日只保留一个最佳值。",
                  "sources": ["Q1"]},
        "boundaries": {"content": "同日重复进行只保留更优成绩;"
                                  "中途退出不记录最佳;跨日旧最佳不再更新。",
                       "sources": ["Q1"]},
        "numbers": {"settled": [
            {"name": "每日关卡数量", "value": "1", "unit": "关/日",
             "range": "1", "calc": "按日期索引现有 20 关",
             "rounding": "向下取整", "basis": "沿用现有 20 关"}],
            "trial": [], "sources": ["Q1"]},
        "feedback": {"content": "进入时显示当日日期与当前最佳;"
                                "结算显示本次步数与最佳对比。",
                     "sources": ["Q1"]},
        "persistence": {"content": "保存当日最佳步数;退出重进后可读;"
                                   "跨日只读旧值,不回写。",
                        "sources": ["Q1"]},
        "acceptance": {"cases": [
            {"initial": "新档,当日未玩", "action": "进入每日挑战完成一局",
             "expected": "记录当日最佳步数,再次进入可读"}],
            "subjective": [], "sources": ["Q1"]},
    }



def test_change_mode_covers_all_invalidation_paths() -> None:
    """变更模式下同样覆盖外部引用变化、权限撤销、冲突与写入失败。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project, mode="design_change")["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        session = record_read(session, SPEC_OTHER_REL, SPEC_OTHER_TEXT,
                              module="章节", purpose="module",
                              call="上一模块读取")["session"]
        # 连续多轮输入未变:读取计划不重读,资料数量保持不变。
        for _round in range(3):
            again = plan_reads(session, _candidates(project))
            check(again["to_read"] == [], "连续多轮输入未变不得重读资料")
            session = again["session"]
        # 外部引用变化:只重读被改目标,无关模块保留。
        changed = _candidates(project)
        for item in changed:
            if item["path"] == SPEC_REL:
                item["sha256"] = sha256_text(SPEC_TEXT + "-外部修改")
        out = invalidate(session, "external_change", paths=[SPEC_REL])
        session = out["session"]
        recheck = plan_reads(session, changed)
        check(_paths(recheck["to_read"]) == [SPEC_REL],
              f"外改后只重读被改目标:{_paths(recheck['to_read'])}")
        check(_paths(recheck["reuse"]) == [PROJECT_REL, CONFIG_REL],
              "无关资料继续复用")
        check(SPEC_OTHER_REL in session["reads"],
              "上一模块资料不被局部外改波及")

        instance = _instance(svc, purpose="spec_sync",
                             resources=["docs/mygamestudio/records/**",
                                        DESIGN_REL])
        channel = _Channel(svc, instance.token)
        existing = {SPEC_REL: read(SPEC_REL), DESIGN_REL: read(DESIGN_REL)}
        plan = change_flow.plan_change(existing, {
            "module": MODULE, "date": DATE, "design_path": DESIGN_REL,
            "change_record_path": f"{RECORDS}/change-每日挑战.md",
            "version_from": "v2", "version_to": "v3",
            "authorization": {"write": True, "sync": True},
        }, _change_material())
        check(plan["status"] == "planned", f"变更应可计划:{plan['status']}")
        # 版本冲突:外部先改目标设计,提交时按实际版本拒绝。
        original_design = read(DESIGN_REL)
        (project / DESIGN_REL).write_text(original_design + "\n外部修改\n",
                                          encoding="utf-8")
        conflicted = change_flow.apply_change(plan, channel, read,
                                              session=session)
        check(conflicted["status"] == "conflict"
              and all(item["path"] != DESIGN_REL for item in channel.writes),
              f"冲突目标不得被覆盖,已写入文件按实际保留:{channel.writes}")
        check(conflicted["session"].get("target_version") is None,
              "冲突后目标版本缓存作废")
        check(SPEC_OTHER_REL in conflicted["session"]["reads"],
              "冲突后无关模块保留")

        # 权限撤销:释放实例后逐次通道校验必然拒绝,不得用缓存跳过。
        svc.release_instance(instance.instance_id)
        plan2 = change_flow.plan_change(
            {SPEC_REL: read(SPEC_REL), DESIGN_REL: read(DESIGN_REL)}, {
                "module": MODULE, "date": DATE, "design_path": DESIGN_REL,
                "change_record_path": f"{RECORDS}/change-每日挑战.md",
                "version_from": "v2", "version_to": "v3",
                "authorization": {"write": True, "sync": True},
            }, _change_material())
        denied = change_flow.apply_change(plan2, channel, read,
                                          session=conflicted["session"])
        check(denied["status"] in {"denied", "conflict"},
              f"撤销后不得写成功:{denied.get('status')}")
        check(channel.scopes or denied.get("rule_stage") == "version",
              "撤销后仍逐次走通道核对")

        # 写入失败:回读不确认时作废目标并如实报告。
        (project / DESIGN_REL).write_text(original_design, encoding="utf-8")
        fresh = _instance(svc, purpose="spec_sync",
                          resources=["docs/mygamestudio/records/**",
                                     DESIGN_REL])
        channel2 = _Channel(svc, fresh.token)
        plan3 = change_flow.plan_change(
            {SPEC_REL: read(SPEC_REL), DESIGN_REL: read(DESIGN_REL)}, {
                "module": MODULE, "date": DATE, "design_path": DESIGN_REL,
                "change_record_path": f"{RECORDS}/change-每日挑战.md",
                "version_from": "v2", "version_to": "v3",
                "authorization": {"write": True, "sync": True},
            }, _change_material())
        failing = _FailingReader(read)
        failing.fail_path = DESIGN_REL
        lost = change_flow.apply_change(plan3, channel2, failing,
                                       session=denied["session"])
        check(lost["status"] in {"save_unconfirmed", "conflict"},
              f"回读失败不得称已保存:{lost.get('status')}")
        check(lost["session"].get("target_version") is None,
              "写入失败后目标版本缓存作废")
        check(SPEC_OTHER_REL in lost["session"]["reads"],
              "写入失败不触发无关模块全量重查")



def test_after_save_detects_history_loss_and_duplicates() -> None:
    """保存后回读能检出历史丢失与重复决定;缺口时作废相关旧结果。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        session = _begin(project)["session"]
        good = (
            "# 每日挑战：决定记录\n\n## 第 1 轮 2026-09-14\n"
            "- 决定者：开发者。日期：2026-09-14。\n"
            "- D 每日挑战·Q1 关卡来源：采纳 A 从现有 20 关抽取\n"
            "  - 来源：开发者逐题选择\n  - 同步状态：待同步\n")
        entries = [{"qid": "Q1", "title": "关卡来源",
                    "value": "A 从现有 20 关抽取"}]
        ok = after_save(session, recorded=good, module=MODULE,
                        entries=entries, content=good,
                        target_version=sha256_text(good))
        check(ok["ok"] is True, f"完整记录应通过回读:{ok['failures']}")
        skipped = ledger(ok["session"], status="skipped")
        check(any("全局" in str(item.get("check")) for item in skipped),
              f"未改核心基线时全局检查记为跳过:{skipped}")
        lost = after_save(ok["session"], recorded=good, module=MODULE,
                          entries=entries, content=good, history=["旧值 未定"])
        check(lost["ok"] is False
              and any("历史" in item for item in lost["failures"]),
              f"历史丢失应检出:{lost['failures']}")
        doubled = good + (
            "- D 每日挑战·Q1 关卡来源：采纳 A 从现有 20 关抽取\n")
        dup = after_save(session, recorded=doubled, module=MODULE,
                         entries=entries, content=doubled)
        check(dup["ok"] is False
              and any("重复" in item for item in dup["failures"]),
              f"重复决定应检出:{dup['failures']}")
        changed = good.replace("采纳 A 从现有 20 关抽取",
                               "采纳 B 每日生成新关")
        missing = after_save(session, recorded=changed, module=MODULE,
                             entries=entries)
        no_sync = after_save(
            session, module=MODULE, entries=entries,
            recorded=good.replace("同步状态：待同步", "同步状态：未知"))
        check(missing["ok"] is False
              and any("缺少决定" in item for item in missing["failures"]),
              f"本轮决定缺失应检出:{missing['failures']}")
        check(no_sync["ok"] is False
              and any("同步状态" in item for item in no_sync["failures"]),
              f"同步状态缺失应检出:{no_sync['failures']}")



def test_new_design_mode_covers_all_invalidation_paths() -> None:
    """新设计模式下覆盖连续多轮、模块结束、外部变化、撤销、冲突与写失败。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project)["session"]
        session = _load_batch(project, session,
                              plan_reads(session, _candidates(project)))
        session = record_read(session, SPEC_OTHER_REL, SPEC_OTHER_TEXT,
                              module="章节", purpose="module",
                              call="上一模块读取")["session"]
        session = record_read(session, DESIGN_REL, read(DESIGN_REL),
                              module=MODULE, purpose="baseline",
                              call="读取核心基线")["session"]
        instance = _instance(svc, purpose="spec_sync",
                             resources=["docs/mygamestudio/records/**",
                                        DESIGN_REL,
                                        "docs/mygamestudio/CONTENT_PRODUCTION.md",
                                        "docs/mygamestudio/VERSION_PLAN.md"])
        channel = _Channel(svc, instance.token)
        settled: dict = {}
        for round_no, answer in enumerate(("Q1 选 A", "Q2 选 A", "Q3 选 A"),
                                          start=1):
            result = run_round(_turn(round_no, answer, settled=settled))
            plan = plan_save(read(RECORD_REL), result,
                             {"record_path": RECORD_REL, "module": MODULE,
                              "round": round_no, "date": DATE,
                              "authorization": {"write": True, "sync": False}},
                             session=session)
            saved = apply_save(plan, channel, read, session=plan["session"])
            check(saved["saved"] is True, f"第 {round_no} 轮应保存成功")
            session = saved["session"]
            for qid, item in result["adopted"].items():
                settled[str(qid)] = item["value"]
        # 模块结束:成稿交付前的收敛统一核对按真实影响一次完成。
        delivery = full_design.plan_delivery(
            _existing_for(read, _delivery_meta()), _delivery_meta(),
            _delivery_material())
        check(delivery["status"] == "planned",
              f"模块结束应可成稿:{delivery.get('missing')}")
        proof = converge(session, {"module": MODULE,
                                   "files": delivery.get("files") or [],
                                   "records": {RECORD_REL: read(RECORD_REL)}})
        check(proof["scope"] == "当前模块"
              and len(ledger(proof["session"], timing="converge")) == 1,
              f"模块结束一次统一核对:{proof['scope']}")
        session = proof["session"]

        # 外部改动引用目标:只重读被改资料,无关模块保留。
        changed = _candidates(project) + [
            {"path": DESIGN_REL, "purpose": "baseline", "module": MODULE,
             "sha256": sha256_text(DESIGN_TEXT + "-外部改动")}]
        out = invalidate(session, "external_change", paths=[DESIGN_REL])
        check(out["stale"] == [DESIGN_REL],
              f"外部改动只作废该目标:{out['stale']}")
        recheck = plan_reads(out["session"], changed)
        check(_paths(recheck["to_read"]) == [DESIGN_REL],
              f"只重读被改目标:{_paths(recheck['to_read'])}")
        check(SPEC_OTHER_REL in out["session"]["reads"],
              "无关模块读取结果保留")
        session = recheck["session"]

        # 授权撤销:逐次通道校验拒绝;重新授权后继续。
        svc.release_instance(instance.instance_id)
        still = _Channel(svc, instance.token)
        result4 = run_round(_turn(4, "Q4 选 A", settled=settled))
        plan4 = plan_save(read(RECORD_REL), result4,
                          {"record_path": RECORD_REL, "module": MODULE,
                           "round": 4, "date": DATE,
                           "authorization": {"write": True, "sync": False}},
                          session=session)
        denied = apply_save(plan4, still, read, session=plan4["session"])
        check(denied["saved"] is False, "撤销后不得写成功")
        check(bool(still.scopes), "撤销后仍逐次走通道核对")
        check(denied["session"]["authorization"]["write"] is False,
              "撤销后会话授权更新")
        check(SPEC_OTHER_REL in denied["session"]["reads"],
              "撤销不触发无关模块全量重查")
        fresh = _instance(svc)
        saved4 = apply_save(plan4, _Channel(svc, fresh.token), read,
                            session=denied["session"])
        check(saved4["saved"] is True, "重新授权后应可继续保存")

        # 版本冲突与写入失败:作废目标身份并如实报告。
        conflicted_session = saved4["session"]
        revised = _turn(5, "Q4 调整为 记录历史最佳", settled=settled)
        revised["boundary_revision"] = {"Q4": "记录历史最佳"}
        plan5 = plan_save(read(RECORD_REL), run_round(revised),
                          {"record_path": RECORD_REL, "module": MODULE,
                           "round": 5, "date": DATE,
                           "authorization": {"write": True, "sync": False}},
                          session=conflicted_session)
        external = read(RECORD_REL) + "\n外部追加\n"
        (project / RECORD_REL).write_text(external, encoding="utf-8")
        clash = apply_save(plan5, _Channel(svc, fresh.token), read,
                           session=plan5["session"])
        check(clash["status"] == "conflict",
              f"外部修改应报版本冲突:{clash.get('status')}")
        check(clash["session"].get("target_version") is None,
              "冲突后目标身份作废")



def test_presave_check_is_reused_only_for_identical_inputs() -> None:
    """保存前核对输入未变时复用结论;回复或目标一变立即重做。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        svc, project = _service(root)
        read = _reader(project)
        session = _begin(project)["session"]
        instance = _instance(svc)
        channel = _Channel(svc, instance.token)
        result = run_round(_turn(1, "Q1 选 A"))
        meta = {"record_path": RECORD_REL, "module": MODULE, "round": 1,
                "date": DATE, "authorization": {"write": True, "sync": False}}
        first = plan_save(read(RECORD_REL), result, meta, session=session)
        check(first["checks"]["reused"] is False,
              "首次核对不得声称复用")
        again = plan_save(read(RECORD_REL), result, meta,
                          session=first["session"])
        check(again["checks"]["reused"] is True
              and again["checks"]["ok"] is True,
              f"同一输入的重复处理应复用已通过结论:{again['checks']}")
        check(any(item.get("reused") for item
                  in ledger(again["session"], timing="before_save")),
              "复用应记入检查台账")
        # 目标内容一变:签名变化,必须重做而不是复用。
        (project / RECORD_REL).write_text(
            "# 每日挑战：决定记录\n\n## 第 1 轮 2026-09-14\n"
            "- 决定者：开发者。日期：2026-09-14。\n"
            "- D 每日挑战·Q1 关卡来源：采纳 A 从现有 20 关按日期抽取\n"
            "  - 来源：开发者逐题选择\n  - 同步状态：待同步\n",
            encoding="utf-8")
        changed = plan_save(read(RECORD_REL), result, meta,
                            session=again["session"])
        check(changed["checks"]["reused"] is False,
              "目标内容变化后不得复用旧核对结论")
        # 矛盾项必须被检出:与已有决定不同且未说明替代关系。
        conflict_result = run_round(_turn(2, "Q1 选 B", settled={"Q1": "A"}))
        conflicting = plan_save(
            read(RECORD_REL), conflict_result,
            {**meta, "round": 2}, session=changed["session"])
        check(conflicting["checks_ok"] is False
              and any("矛盾" in gap for gap in conflicting["checks"]["gaps"]),
              f"与已有决定的矛盾应检出:{conflicting.get('checks')}")
        # 可写范围:目标不在范围内时保存前即判缺口,不进入写入。
        scoped = plan_save(
            read(RECORD_REL), result,
            {**meta, "authorization": {"write": True, "sync": False,
                                       "scope": ["docs/other/**"]}},
            session=changed["session"])
        check(scoped["checks_ok"] is False
              and any("可写范围" in gap for gap in scoped["checks"]["gaps"]),
              f"越界目标应在保存前检出:{scoped.get('checks')}")
        check(not channel.writes, "保存前缺口不得触发写入")


TESTS = (
    test_read_plan_reuses_unchanged_and_excludes_unrelated,
    test_round_save_checks_before_and_after_without_global_rerun,
    test_precheck_gap_blocks_save_without_disk_checks,
    test_invalidation_only_drops_affected_parts,
    test_revoked_authorization_rechecks_only_affected,
    test_conflict_and_write_failure_invalidate_target,
    test_converge_runs_once_with_real_scope,
    test_report_keeps_save_result_and_short_details,
    test_full_design_delivery_reuses_reads_and_records_writes,
    test_change_flow_reuses_reads_and_records_writes,
    test_spec_handoff_and_removal_share_timing,
    test_measure_counts_actual_events,
    test_change_mode_covers_all_invalidation_paths,
    test_new_design_mode_covers_all_invalidation_paths,
    test_presave_check_is_reused_only_for_identical_inputs,
    test_after_save_detects_history_loss_and_duplicates,
    test_game_design_entry_points_to_checks_seam,
)


def main() -> int:
    return run_theme("减少重复读取与检查(检查时机与复用)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
