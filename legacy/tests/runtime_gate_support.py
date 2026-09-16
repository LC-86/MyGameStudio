#!/usr/bin/env python3
"""受控写入(运行保障)行为主题检查的共享准备(任务票 12)。

只放各主题共用的最小准备代码:导入路径与接缝、失败清单工厂、审计读取、
项目与服务的临时夹具、实例签发助手。判定一律由各主题经真实
``mgs_runtime`` / ``mcp_gate`` 公开接缝作出,本 module 不复制生产规则,
也不断言任何私有检查步骤。每个主题经 ``make_checker`` 各自持有失败清单,
互不串扰;原总入口聚合各主题清单,运行方式与退出含义不变。
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tests"))
sys.path.insert(0, str(REPO_ROOT / "legacy" / "runtime"))

from mgs_runtime import GateService  # noqa: E402
import mcp_gate  # noqa: E402

__all__ = [
    "REPO_ROOT", "GateService", "mcp_gate", "make_checker", "run_theme",
    "audit_lines", "setup_project", "setup_service", "new_instance",
]


def make_checker():
    """返回 (FAILURES, check):每个主题独立持有,聚合时不互相污染。"""

    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    return failures, check


def run_theme(title: str, tests: tuple, failures: list[str]) -> int:
    """依次运行主题内检查函数,统一打印结果并返回进程退出码。"""

    for test in tests:
        test()
    if failures:
        print(f"FAIL ({len(failures)} 项) [{title}]:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"OK: {title} 检查全部通过")
    return 0


def audit_lines(runtime_root: Path) -> list[dict]:
    audit_path = runtime_root / "audit" / "audit.jsonl"
    if not audit_path.is_file():
        return []
    return [json.loads(line) for line in audit_path.read_text().splitlines()
            if line.strip()]


def setup_project(root: Path) -> Path:
    project = root / "project"
    (project / "docs/mygamestudio/work/01-status").mkdir(parents=True)
    (project / "src").mkdir(parents=True)
    (project / "docs/mygamestudio/PROJECT.md").write_text("PROJECT-ORIGINAL\n")
    (project / "docs/mygamestudio/GAME_DESIGN.md").write_text("DESIGN-ORIGINAL\n")
    (project / "src/player.js").write_text("// ORIGINAL\n")
    return project


def setup_service(root: Path) -> tuple[GateService, Path]:
    project = setup_project(root)
    runtime_root = root / "runtime"
    svc = GateService(runtime_root)
    svc.init_policy(
        project_root=project,
        roles={
            "producer": ["docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/*/task.md"],
            "design": ["docs/mygamestudio/GAME_DESIGN.md", "prototypes/**"],
            "implement": ["src/**", "assets/**", "docs/mygamestudio/work/*/results/**"],
        },
        purposes={"production": None, "prototype": ["prototypes/**"]},
    )
    return svc, project


def new_instance(svc: GateService, role: str, resources: list[str],
                 purpose: str = "production", ttl: int = 1800,
                 task: str = "T") -> tuple[str, str]:
    inst = svc.create_instance(role=role, task=task, purpose=purpose,
                               resources=resources, ttl_seconds=ttl)
    return inst.instance_id, inst.token
