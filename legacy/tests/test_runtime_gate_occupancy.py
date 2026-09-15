#!/usr/bin/env python3
"""受控写入的占用:回收、到期悬挂占用与释放中断缺口。

任务票 12 从 tests/test_runtime_gate.py 的原始总入口按真实行为主题拆出;
每条 check 的条件、消息与断言对象与原案例逐字一致(任务票 15 的
reclaim_locks/list_locks 占用回收接缝),仅重组位置。原总入口仍聚合本
主题。本主题可直接运行:

    python3 -B tests/test_runtime_gate_occupancy.py
"""

import shutil
import sys
import tempfile
import time
from pathlib import Path

from runtime_gate_support import GateService, make_checker, run_theme

FAILURES, check = make_checker()

TARGET = "docs/mygamestudio/work/15-race/notes.md"
RESOURCES = ["docs/mygamestudio/work/15-race/**"]


def _race_service(root: Path):
    race_root = root / "race-runtime"
    race_project = root / "race-project"
    (race_project / "docs/mygamestudio/work/15-race").mkdir(parents=True)
    race_svc = GateService(race_root)
    race_svc.init_policy(
        project_root=race_project,
        roles={"implement": ["docs/mygamestudio/work/15-race/**"]},
        purposes={"production": None},
    )

    def race_instance(task: str, ttl: int = 1800) -> tuple[str, str]:
        inst = race_svc.create_instance(role="implement", task=task,
                                        purpose="production",
                                        resources=RESOURCES,
                                        ttl_seconds=ttl)
        return inst.instance_id, inst.token

    return race_svc, race_project, race_instance


def test_reclaim_and_expiry() -> None:
    """案例 23/24:活跃占用不可回收、释放幂等回收、到期悬挂占用回收。"""

    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-occ-"))
    try:
        race_svc, race_project, race_instance = _race_service(root)
        target = TARGET

        # 23. 占用回收(任务票 15):先撤销旧执行能力,再回收占用。
        #     活跃实例的占用不可回收(拒绝);释放/过期后才可回收;
        #     回收后新执行者可接管同一资源。
        aid, atok = race_instance("T-hold")
        res = race_svc.write(atok, target, "HOLDER\n")
        check(res["decision"] == "allow", f"持有实例首写应成功,实际 {res}")
        bid, btok = race_instance("T-takeover")
        res = race_svc.write(btok, target, "TAKEOVER\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"占用期间新执行者写入应被拒,实际 {res}")
        # 活跃实例的占用不可回收:拒绝并保持占用
        result = race_svc.reclaim_locks(aid)
        check(result["ok"] is False and result.get("active") is True,
              f"活跃实例的占用回收应被拒绝,实际 {result}")
        res = race_svc.write(btok, target, "TAKEOVER\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              "拒绝回收后占用应保持,新执行者仍被拒")
        locks = race_svc.list_locks()
        check(target in locks.get("locks", {})
              and locks["locks"][target]["instance_id"] == aid,
              f"list_locks 应回报当前占用,实际 {locks}")
        # 释放(撤销执行能力)本身回收占用;再回收为幂等空操作
        race_svc.release_instance(aid)
        result = race_svc.reclaim_locks(aid)
        check(result["ok"] is True and result["reclaimed"] == 0,
              f"释放后重复回收应为幂等空操作,实际 {result}")
        res = race_svc.write(btok, target, "TAKEOVER\n")
        check(res["decision"] == "allow", f"释放后新执行者应可接管,实际 {res}")
        race_svc.release_instance(bid)

        # 24. 到期实例的悬挂占用:实例在有效期内取得占用后过期,
        #     令牌失效(写被拒)但占用记录悬挂;回收按到期放行。
        xid, xtok = race_instance("T-expire", ttl=1)
        res = race_svc.write(xtok, target, "EXPIRE\n")
        check(res["decision"] == "allow", f"短期实例首写应成功,实际 {res}")
        time.sleep(1.2)
        res = race_svc.write(xtok, target, "EXPIRE2\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "identity",
              f"过期令牌写入应被拒(identity),实际 {res}")
        kid, ktok = race_instance("T-takeover-expire")
        res = race_svc.write(ktok, target, "TAKEOVER2\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"过期实例的占用仍应阻塞新执行者,实际 {res}")
        result = race_svc.reclaim_locks(xid)
        check(result["ok"] is True and result["reclaimed"] >= 1,
              f"到期实例的占用回收应放行并释放,实际 {result}")
        res = race_svc.write(ktok, target, "TAKEOVER2\n")
        check(res["decision"] == "allow", f"回收后新执行者应可接管,实际 {res}")
        race_svc.release_instance(kid)
        result = race_svc.reclaim_locks("i-nonexistent")
        check(result["ok"] is False and result["found"] is False,
              f"未知实例回收应被拒,实际 {result}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_release_crash_gap() -> None:
    """案例 24b:release 两次落盘之间中断留下「已释放但仍持占用」缺口。"""

    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-gap-"))
    try:
        race_svc, race_project, race_instance = _race_service(root)
        target = TARGET

        # 24b. 释放流程中断缺口:release_instance 在登记与占用两次落盘之间
        #      崩溃会留下「已释放但仍持有占用」状态(直接构造该终态验证);
        #      再次 release 不再处理(found=False),reclaim_locks 补上回收。
        yid, ytok = race_instance("T-crashgap")
        res = race_svc.write(ytok, target, "GAP\n")
        check(res["decision"] == "allow", f"缺口演示实例首写应成功,实际 {res}")
        with race_svc._locked():
            records = race_svc._read_json("instances.json", [])
            for record in records:
                if record["instance_id"] == yid:
                    record["released"] = True
            race_svc._write_json("instances.json", records)
            # 模拟:instances.json 落盘后、locks.json 落盘前进程被杀
        res = race_svc.write(ytok, target, "GAP2\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "identity",
              "已释放实例的令牌应立即失效(持续进程不能再写)")
        zid, ztok = race_instance("T-takeover-gap")
        res = race_svc.write(ztok, target, "TAKEOVER3\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"中断缺口下占用仍悬挂,实际 {res}")
        release_result = race_svc.release_instance(yid)
        check(release_result["found"] is False,
              "再次 release 对已释放记录不再处理(found=False)")
        res = race_svc.write(ztok, target, "TAKEOVER3\n")
        check(res["decision"] == "deny",
              "再次 release 不应顺带回收悬挂占用(现状),由回收接缝负责")
        result = race_svc.reclaim_locks(yid)
        check(result["ok"] is True and result["reclaimed"] >= 1,
              f"回收接缝应补上中断缺口的占用回收,实际 {result}")
        res = race_svc.write(ztok, target, "TAKEOVER3\n")
        check(res["decision"] == "allow", f"缺口回收后新执行者应可接管,实际 {res}")
        race_svc.release_instance(zid)
    finally:
        shutil.rmtree(root, ignore_errors=True)


TESTS = (test_reclaim_and_expiry, test_release_crash_gap)

if __name__ == "__main__":
    sys.exit(run_theme("受控写入占用回收与释放缺口", TESTS, FAILURES))
