#!/usr/bin/env python3
"""核心基线指纹与受影响任务。

任务票 11 从 tests/test_records_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_records_baseline.py
"""

import json
import sys
import tempfile
from pathlib import Path

from records_backend_support import (
    PLAN_TASK_TEMPLATE, _register_fingerprint, counted_config_reads,
    make_checker, make_config_selfmap_project, make_project,
    run_cli, run_theme, scoped_read_counter,
)

import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_baseline_report_states() -> None:
    """内容指纹四态:一致/指纹未登记/格式修正漂移/实质变更漂移(任务票 15)。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        docs = root / "docs" / "mygamestudio"
        # GAME_DESIGN:声明 v4 并登记指纹
        design = docs / "GAME_DESIGN.md"
        design.write_text(
            "# 当前游戏需求与设计\n\n维护责任:方案设计。基线版本:v4。\n"
            "\n- 回合时长 45 秒,结束即结算\n", encoding="utf-8")
        _register_fingerprint(design, "基线版本:v4。")
        report = mgs_records.baseline_report(root)
        states = {d["path"].split("/")[-1]: d["status"] for d in report["docs"]}
        check(states.get("GAME_DESIGN.md") == "一致",
              f"登记指纹且内容未变应为一致,实际 {states}")
        check(report["ok"] is True, "无实质变更时 baseline 应 ok")

        # PROJECT 未登记指纹 → 指纹未登记(不判漂移)
        check(states.get("PROJECT.md") == "指纹未登记",
              f"未登记指纹的基线应报指纹未登记,实际 {states}")

        # 格式修正(仅空白变化,无字符增删)→ 疑似格式修正,不作废(ok 保持)
        design.write_text(
            design.read_text(encoding="utf-8").replace(
                "- 回合时长 45 秒,结束即结算\n",
                "- 回合时长 45 秒,\t结束即结算\n"), encoding="utf-8")
        report = mgs_records.baseline_report(root)
        states = {d["path"].split("/")[-1]: d["status"] for d in report["docs"]}
        check(states.get("GAME_DESIGN.md") == "内容已变(疑似格式修正)",
              f"仅空白变化应判疑似格式修正,实际 {states}")
        check(report["ok"] is True, "格式修正不应判为需要重审(ok 应保持 True)")

        # 实质变更(字符增删,版本号未同步)→ 实质变更,ok False
        design.write_text(
            design.read_text(encoding="utf-8").replace(
                "回合时长 45 秒", "回合时长 50 秒"), encoding="utf-8")
        report = mgs_records.baseline_report(root)
        states = {d["path"].split("/")[-1]: d["status"] for d in report["docs"]}
        check(states.get("GAME_DESIGN.md") == "内容已变(实质变更)",
              f"字符实质变化应判实质变更,实际 {states}")
        check(report["ok"] is False, "存在实质变更未同步时 baseline 不应 ok")

        # 文件缺失 → 文件缺失
        (docs / "TECH_DESIGN.md").unlink()
        report = mgs_records.baseline_report(root)
        states = {d["path"].split("/")[-1]: d["status"] for d in report["docs"]}
        check(states.get("TECH_DESIGN.md") == "文件缺失",
              f"核心基线文件缺失应如实报告,实际 {states}")


def test_baseline_report_affected_tasks() -> None:
    """受影响任务识别:引用旧版本即列出;已完成/待验收保留完成事实语义。"""

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        docs = root / "docs" / "mygamestudio"
        design = docs / "GAME_DESIGN.md"
        design.write_text("# 当前游戏需求与设计\n\n基线版本:v4。\n", encoding="utf-8")
        work = docs / "work"
        (work / "05-gull-swoop").mkdir(parents=True)
        (work / "05-gull-swoop" / "task.md").write_text(PLAN_TASK_TEMPLATE.format(
            title="海鸥俯冲", identity="05-gull-swoop", triage="ready-for-agent",
            progress="待执行", goal="实现海鸥俯冲", deliver="src 代码", scope="src/**",
            capability="文件读写", executor="Agent(制作实现)", acceptance="行为检查",
            deps="无", coordination="无", missing="无", index="(暂无)").replace(
            "GAME_DESIGN v2「本轮可执行规格」",
            "GAME_DESIGN v2「当前规则与流程」"), encoding="utf-8")
        (work / "02-tide-timer").mkdir(parents=True)
        (work / "02-tide-timer" / "task.md").write_text(PLAN_TASK_TEMPLATE.format(
            title="潮汐倒计时", identity="02-tide-timer", triage="ready-for-agent",
            progress="待验收", goal="实现倒计时", deliver="src 代码", scope="src/**",
            capability="文件读写", executor="Agent(制作实现)", acceptance="行为检查",
            deps="无", coordination="无", missing="无", index="(暂无)").replace(
            "GAME_DESIGN v2「本轮可执行规格」",
            "GAME_DESIGN v2;TECH_DESIGN v1"), encoding="utf-8")
        (work / "06-fresh").mkdir(parents=True)
        (work / "06-fresh" / "task.md").write_text(PLAN_TASK_TEMPLATE.format(
            title="新任务", identity="06-fresh", triage="ready-for-agent",
            progress="待执行", goal="新任务", deliver="示例", scope="src/**",
            capability="文件读写", executor="Agent(制作实现)", acceptance="行为检查",
            deps="无", coordination="无", missing="无", index="(暂无)").replace(
            "GAME_DESIGN v2「本轮可执行规格」",
            "GAME_DESIGN v4「当前规则与流程」与 PROJECT.md 当前目标"), encoding="utf-8")
        report = mgs_records.baseline_report(root)
        affected = {item["identity"]: item for item in report["affected_tasks"]}
        check("05-gull-swoop" in affected,
              f"引用 GAME_DESIGN v2(当前 v4)的任务应列为受影响,实际 {sorted(affected)}")
        entry = affected.get("05-gull-swoop", {})
        check(entry.get("ref_version") == "v2" and entry.get("current_version") == "v4",
              f"受影响条目应记录引用版本与当前版本,实际 {entry}")
        check(not entry.get("completion_fact"),
              "待执行任务的受影响条目不应带完成事实说明")
        check("02-tide-timer" in affected,
              "待验收任务引用旧版本同样应列为受影响")
        done_entry = affected.get("02-tide-timer", {})
        check(done_entry.get("progress") == "待验收"
              and "保留原版本" in (done_entry.get("completion_fact") or "")
              and "不自动算作满足新目标" in (done_entry.get("completion_fact") or ""),
              f"待验收受影响条目应声明完成事实保留语义,实际 {done_entry}")
        check("06-fresh" not in affected,
              "引用当前版本或无版本号引用的任务不应列为受影响")
        check("版本号未同步" in report["note"] or "指纹" in report["note"],
              "baseline 输出应附处理说明 note")


def test_baseline_cli() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        result = run_cli("baseline", "--project", str(root))
        check(result.returncode == 0,
              f"CLI baseline 无实质变更应退出 0:{result.stdout[:200]}")
        data = json.loads(result.stdout)
        check(isinstance(data.get("docs"), list) and data["docs"],
              "CLI baseline 应输出 docs 列表")
        docs = root / "docs" / "mygamestudio"
        design = docs / "GAME_DESIGN.md"
        design.write_text("# 当前游戏需求与设计\n\n基线版本:v2。\n- 规则\n",
                          encoding="utf-8")
        _register_fingerprint(design, "基线版本:v2。")
        design.write_text(design.read_text(encoding="utf-8") + "- 新增规则\n",
                          encoding="utf-8")
        result = run_cli("baseline", "--project", str(root))
        check(result.returncode == 1, "CLI baseline 存在实质变更未同步应以退出码 1 表达")


def test_baseline_reads_config_and_core_docs_once() -> None:
    """AC1/AC2/READ-04:baseline 同次复用配置与核心文档原文一次。

    CONFIG 只读一次;每份核心文档只读一次,同一原文同时推导逻辑版本与双
    指纹;下一次调用重新读取(不跨调用缓存)。双指纹三态与完成事实语义
    由 test_baseline_report_states/affected_tasks 逐项覆盖,此处只验证口径。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        design = root / "docs" / "mygamestudio" / "GAME_DESIGN.md"
        design.write_text("# 当前游戏需求与设计\n\n基线版本:v2。\n- 规则\n",
                          encoding="utf-8")
        _register_fingerprint(design, "基线版本:v2。")

        with scoped_read_counter(root) as counter:
            first = mgs_records.baseline_report(root)
        check(counter.config_reads() == 1,
              f"baseline 应只读 CONFIG 原文一次,实际 {counter.by_path}")
        core_reads = {Path(rel).name: n for rel, n in counter.by_path.items()
                      if Path(rel).name in ("PROJECT.md", "GAME_DESIGN.md",
                                            "TECH_DESIGN.md")}
        check(core_reads == {"PROJECT.md": 1, "GAME_DESIGN.md": 1,
                             "TECH_DESIGN.md": 1},
              f"baseline 每份核心文档应只读一次(版本与指纹同一原文),实际 "
              f"{counter.by_path}")
        by_name = {d["path"].split("/")[-1]: d for d in first["docs"]}
        check(by_name["GAME_DESIGN.md"]["status"] == "一致"
              and by_name["GAME_DESIGN.md"]["declared_version"] == "v2",
              f"同一原文应同时给出逻辑版本与登记指纹结论,实际 "
              f"{by_name['GAME_DESIGN.md']}")

        # 下一次调用重新读取:仅空白差异应判疑似格式修正(语义保持)
        design.write_text(design.read_text(encoding="utf-8").replace(
            "- 规则\n", "- 规则\t\n"), encoding="utf-8")
        second = mgs_records.baseline_report(root)
        states = {d["path"].split("/")[-1]: d["status"] for d in second["docs"]}
        check(states.get("GAME_DESIGN.md") == "内容已变(疑似格式修正)",
              f"下一次调用应重新读取并看到仅空白差异,实际 {states}")
        check(second["ok"] is True, "疑似格式修正不应判为需要重审")

def test_baseline_docmap_alias_reuses_one_read() -> None:
    """spec 10:核心文档按解析后的实际路径复用已读文本(PR #28 复审 SP-2)。

    同一物理文件经 ``docs/mygamestudio/GAME_DESIGN.md`` 与
    ``docs/mygamestudio/./GAME_DESIGN.md`` 两种合法映射写法出现时,本次调用
    只实际读取一次:逻辑版本、双指纹与受影响任务判断都从同一份原文推导,
    不因映射写法差异实际读取两次、混入不同时点的结果;各映射路径仍分别
    定位输出。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp))
        docs = root / "docs" / "mygamestudio"
        config = docs / "CONFIG.md"
        config.write_text(config.read_text(encoding="utf-8").replace(
            "| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |",
            "| 技术设计 | docs/mygamestudio/TECH_DESIGN.md | 制作实现 |\n"
            "| 游戏需求与设计(别名) | docs/mygamestudio/./GAME_DESIGN.md | 方案设计 |"),
            encoding="utf-8")
        design = docs / "GAME_DESIGN.md"
        design.write_text("# 当前游戏需求与设计\n\n基线版本:v2。\n- 规则\n",
                          encoding="utf-8")
        work = docs / "work" / "07-alias-ref"
        work.mkdir(parents=True)
        (work / "task.md").write_text(PLAN_TASK_TEMPLATE.format(
            title="别名引用任务", identity="07-alias-ref", triage="ready-for-agent",
            progress="待执行", goal="演示别名引用", deliver="示例", scope="src/**",
            capability="文件读写", executor="Agent(制作实现)", acceptance="行为检查",
            deps="无", coordination="无", missing="无", index="(暂无)").replace(
            "GAME_DESIGN v2「本轮可执行规格」",
            "docs/mygamestudio/./GAME_DESIGN.md v2"), encoding="utf-8")

        # 首次实际读取取得 v2 后,同一物理文件变为 v3:若按映射写法各读一次,
        # 两个映射位置会分别拿到 v2 与 v3,报告出现混合时点结论(审查反例)。
        target = design.resolve()
        real_read_text = Path.read_text
        reads = {"count": 0}

        def counted_read_text(path_self, *args, **kwargs):
            text = real_read_text(path_self, *args, **kwargs)
            if path_self.resolve() == target:
                reads["count"] += 1
                if reads["count"] == 1:
                    design.write_text(
                        "# 当前游戏需求与设计\n\n基线版本:v3。\n- 新规则\n",
                        encoding="utf-8")
            return text

        Path.read_text = counted_read_text  # type: ignore[method-assign]
        try:
            report = mgs_records.baseline_report(root)
        finally:
            Path.read_text = real_read_text

        check(reads["count"] == 1,
              f"同一物理文件的两种映射写法应只实际读取一次,实际 {reads['count']} 次")
        rows = [d for d in report["docs"]
                if d["path"].replace("./", "").endswith("GAME_DESIGN.md")]
        check(len(rows) == 2,
              f"两种映射位置都应保留输出定位,实际 {[d['path'] for d in rows]}")
        declared = {d["declared_version"] for d in rows}
        fingerprints = {d["current_fingerprint"] for d in rows}
        check(declared == {"v2"},
              f"两种映射位置应从同一份已读原文推导逻辑版本,实际 {declared}")
        check(len(fingerprints) == 1,
              f"两种映射位置应从同一份已读原文推导指纹,实际 {fingerprints}")
        check(not report["affected_tasks"],
              f"任务引用 v2 与本次已读原文一致,不应列为受影响,实际 "
              f"{report['affected_tasks']}")


def test_config_self_mapping_reuses_first_read() -> None:
    """spec 9/10:顶层已取得的 CONFIG 原文纳入同次文档复用(R2-SP-1)。

    文档映射含 CONFIG 自映射时,同一次顶层调用不得把 load_config 已读的
    CONFIG 原文再读一遍。首读后同次把 CONFIG 改为 v2:读两次会以第二次原文
    判出「CONFIG 当前 v2,任务引用 v1」的假漂移;修复后只读一次、受影响任务
    为空;下一次顶层调用重新读取,如实反映 v2(跨调用刷新语义保持)。
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = make_config_selfmap_project(Path(tmp))
        config_path = root / "docs" / "mygamestudio" / "CONFIG.md"
        rewritten = config_path.read_text(encoding="utf-8").replace(
            "基线版本:v1。", "基线版本:v2。")

        with counted_config_reads(config_path, rewritten) as reads:
            report = mgs_records.baseline_report(root)
        check(reads["count"] == 1,
              f"CONFIG 自映射时应复用顶层已读原文、只实际读取一次,"
              f"实际 {reads['count']} 次")
        check(not report["affected_tasks"],
              f"任务引用 v1 与本次已读原文一致,不应列为受影响,实际 "
              f"{report['affected_tasks']}")

        # 下一次顶层调用重新读取:磁盘已是 v2,应如实列出受影响任务。
        second = mgs_records.baseline_report(root)
        affected = {item["identity"]: item for item in second["affected_tasks"]}
        entry = affected.get("08-config-ref", {})
        check(entry.get("ref_version") == "v1" and entry.get("current_version") == "v2",
              f"下一次调用应重新读取并反映 v2,实际 {entry}")


TESTS = (
    test_baseline_report_states,
    test_config_self_mapping_reuses_first_read,
    test_baseline_report_affected_tasks,
    test_baseline_cli,
    test_baseline_reads_config_and_core_docs_once,
    test_baseline_docmap_alias_reuses_one_read,
)

if __name__ == "__main__":
    sys.exit(run_theme("核心基线指纹与受影响任务", TESTS, FAILURES))
