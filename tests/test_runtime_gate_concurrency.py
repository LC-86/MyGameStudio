#!/usr/bin/env python3
"""受控写入的真实多进程并发竞争与规范化别名。

任务票 12 从 tests/test_runtime_gate.py 的原始总入口按真实行为主题拆出;
每条 check 的条件、消息与断言对象与原案例逐字一致(任务票 15 的第 25 项
跨进程并发、规范化别名、过期输入与独立资源并行),仅重组位置。并发探针
使用本主题在 /tmp 创建的临时运行根与子进程,互不干扰。原总入口仍聚合
本主题。本主题可直接运行:

    python3 -B tests/test_runtime_gate_concurrency.py
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from runtime_gate_support import GateService, REPO_ROOT, make_checker, run_theme

FAILURES, check = make_checker()

TARGET = "docs/mygamestudio/work/15-race/notes.md"
RESOURCES = ["docs/mygamestudio/work/15-race/**"]
RACE_TARGET = "docs/mygamestudio/work/15-race/race.md"


def _race_cluster(root: Path):
    """搭建 25a-25c 的并发夹具:服务、实例工厂与跨进程写入启动器。"""

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
                                        resources=RESOURCES, ttl_seconds=ttl)
        return inst.instance_id, inst.token

    driver = root / "race_driver.py"
    driver.write_text(
        "import json, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from mgs_runtime import GateService\n"
        "runtime_root, token, path, content, expected = sys.argv[2:]\n"
        "svc = GateService(runtime_root)\n"
        "res = svc.write(token, path, content,\n"
        "                expected_sha256=(expected or None))\n"
        "print(json.dumps(res))\n",
        encoding="utf-8")
    runtime_src = str(REPO_ROOT / "plugin" / "runtime")

    def race_proc(token: str, path: str, content: str, expected: str = ""):
        return subprocess.Popen(
            [sys.executable, "-B", str(driver), runtime_src,
             str(race_root), token, path, content, expected],
            stdout=subprocess.PIPE, text=True)

    return race_svc, race_project, race_instance, race_proc


def test_concurrent_writers() -> None:
    """案例 25a-25c:同资源竞争恰一个有效写入者;别名与过期输入语义。"""

    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-conc-"))
    try:
        race_svc, race_project, race_instance, race_proc = _race_cluster(root)

        # 25. 真实并发竞争(任务票 15):两个独立进程经同一运行根同时写入同一
        #     资源——文件锁串行化后恰一个有效写入者,另一个 occupancy 拒绝;
        #     规范化路径(./ 与项目内符号链接别名)映射到同一占用;
        #     过期输入(expected_sha256 不符)被拒,不覆盖他人成果;
        #     独立资源并行写入互不阻塞。
        # 25a. 同一资源:两进程同时启动,恰一个 allow
        race_target2 = RACE_TARGET
        cid, ctok = race_instance("T-race-a", ttl=1800)
        did, dtok = race_instance("T-race-b", ttl=1800)
        p1 = race_proc(ctok, race_target2, "FROM-A\n")
        p2 = race_proc(dtok, race_target2, "FROM-B\n")
        out1 = json.loads(p1.communicate(timeout=30)[0])
        out2 = json.loads(p2.communicate(timeout=30)[0])
        decisions = sorted([out1["decision"], out2["decision"]])
        check(decisions == ["allow", "deny"],
              f"并发竞争应恰有一个有效写入者,实际 {out1.get('decision')}/{out2.get('decision')}")
        denied = out1 if out1["decision"] == "deny" else out2
        allowed = out2 if out1["decision"] == "deny" else out1
        check(denied["rule_stage"] == "occupancy",
              f"竞争失败方应被占用拒绝,实际 {denied}")
        check(allowed["rule_stage"] == "granted", f"竞争胜者应为 granted,实际 {allowed}")
        final_content = (race_project / race_target2).read_text()
        check(final_content in ("FROM-A\n", "FROM-B\n"),
              f"最终内容应恰为胜者写入,实际 {final_content!r}")

        # 25b. 规范化别名:竞争胜者持有占用后,经 ./ 折叠路径与项目内符号
        #      链接别名写入同一资源,仍被占用拒绝(不能靠别名绕过单写入者)。
        winner_token = ctok if out1["decision"] == "allow" else dtok
        alias_dot = "docs/mygamestudio/work/15-race/./race.md"
        res = race_svc.write(winner_token, alias_dot, "ALIAS\n")
        check(res["decision"] == "allow",
              "同一实例经 ./ 别名写自身占用资源应成功(同一占用者)")
        loser_token = dtok if out1["decision"] == "allow" else ctok
        res = race_svc.write(loser_token, alias_dot, "ALIAS\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"他方经 ./ 别名写被占资源应被拒,实际 {res}")
        (race_project / "docs/mygamestudio/work/alias15").symlink_to("15-race")
        res = race_svc.write(loser_token,
                             "docs/mygamestudio/work/alias15/race.md", "ALIAS\n")
        check(res["decision"] == "deny" and res["rule_stage"] == "occupancy",
              f"项目内符号链接别名写被占资源应被拒(占用按规范化标识),实际 {res}")

        # 25c. 过期输入:释放胜者后,新执行者持过期的 expected_sha256 写入
        #      应被 version 拒绝,不覆盖他人已写入成果;以实际内容指纹重试才成功。
        _stale_input_after_release(race_svc, race_project, race_target2,
                                   race_instance, cid, did)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _stale_input_after_release(race_svc, race_project, race_target2,
                               race_instance, cid: str, did: str) -> None:
    """案例 25c:释放胜者后,过期 expected_sha256 被 version 拒绝。"""

    race_svc.release_instance(cid)
    race_svc.release_instance(did)
    final_content = (race_project / race_target2).read_text()
    eid, etok = race_instance("T-stale")
    stale = hashlib.sha256(b"never-existed").hexdigest()
    res = race_svc.write(etok, race_target2, "STALE\n", expected_sha256=stale)
    check(res["decision"] == "deny" and res["rule_stage"] == "version",
          f"过期输入应被版本校验拒绝,实际 {res}")
    check((race_project / race_target2).read_text() == final_content,
          "被拒后他人成果字节应保持不变")
    current = hashlib.sha256(
        (race_project / race_target2).read_bytes()).hexdigest()
    res = race_svc.write(etok, race_target2, "REFRESH\n",
                         expected_sha256=current)
    check(res["decision"] == "allow", f"按实际内容版本核对后写入应成功,实际 {res}")


def test_independent_resources_parallel() -> None:
    """案例 25d:两进程同时写不同资源,互不阻塞。"""

    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-par-"))
    try:
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

        driver = root / "race_driver.py"
        driver.write_text(
            "import json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from mgs_runtime import GateService\n"
            "runtime_root, token, path, content, expected = sys.argv[2:]\n"
            "svc = GateService(runtime_root)\n"
            "res = svc.write(token, path, content,\n"
            "                expected_sha256=(expected or None))\n"
            "print(json.dumps(res))\n",
            encoding="utf-8")
        runtime_src = str(REPO_ROOT / "plugin" / "runtime")

        def race_proc(token: str, path: str, content: str, expected: str = ""):
            return subprocess.Popen(
                [sys.executable, "-B", str(driver), runtime_src,
                 str(race_root), token, path, content, expected],
                stdout=subprocess.PIPE, text=True)

        # 25d. 独立资源并行:两进程同时写不同资源,互不阻塞
        fid, ftok = race_instance("T-par-a")
        gid, gtok = race_instance("T-par-b")
        p1 = race_proc(ftok, "docs/mygamestudio/work/15-race/par-a.md", "PA\n")
        p2 = race_proc(gtok, "docs/mygamestudio/work/15-race/par-b.md", "PB\n")
        out1 = json.loads(p1.communicate(timeout=30)[0])
        out2 = json.loads(p2.communicate(timeout=30)[0])
        check(out1["decision"] == "allow" and out2["decision"] == "allow",
              f"独立资源并行写入应互不阻塞,实际 {out1.get('decision')}/{out2.get('decision')}")
        race_svc.release_instance(fid)
        race_svc.release_instance(gid)
    finally:
        shutil.rmtree(root, ignore_errors=True)


TESTS = (test_concurrent_writers, test_independent_resources_parallel)

if __name__ == "__main__":
    sys.exit(run_theme("受控写入真实多进程并发竞争", TESTS, FAILURES))
