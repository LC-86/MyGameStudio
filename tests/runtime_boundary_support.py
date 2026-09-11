#!/usr/bin/env python3
"""间接写入与检查故障边界检查的共享准备(任务票 12)。

只放各主题共用的最小准备代码:导入路径与接缝、失败清单工厂、项目/服务
夹具、字节指纹助手,以及以真实子进程驱动 ``mcp_gate.py`` JSON-RPC 的通道
接缝类。判定一律由各主题经真实 ``mgs_runtime`` / ``mcp_gate`` 公开接缝
作出,本 module 不复制生产规则。每个主题经 ``make_checker`` 各自持有失败
清单,互不串扰;原总入口聚合各主题清单,运行方式与退出含义不变。
"""

import hashlib
import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "plugin" / "runtime"))

from mgs_runtime import GateService  # noqa: E402

GATE_SCRIPT = REPO_ROOT / "plugin" / "runtime" / "mcp_gate.py"

__all__ = [
    "REPO_ROOT", "GATE_SCRIPT", "GateService", "make_checker", "run_theme",
    "sha256_bytes", "setup_project", "init_service", "GateChannel",
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def setup_project(root: Path) -> Path:
    project = root / "project"
    (project / "docs/mygamestudio").mkdir(parents=True)
    (project / "src").mkdir(parents=True)
    (project / "docs/mygamestudio/PROJECT.md").write_text("PROJECT-ORIGINAL\n")
    (project / "docs/mygamestudio/GAME_DESIGN.md").write_text("DESIGN-ORIGINAL\n")
    (project / "src/player.js").write_text("// ORIGINAL\n")
    return project


def init_service(runtime_root: Path, project: Path) -> GateService:
    svc = GateService(runtime_root)
    svc.init_policy(
        project_root=project,
        roles={
            "producer": ["docs/mygamestudio/PROJECT.md", "docs/mygamestudio/work/*/task.md"],
            "design": ["docs/mygamestudio/GAME_DESIGN.md", "prototypes/**"],
            "implement": ["src/**", "docs/mygamestudio/work/*/results/**"],
        },
        purposes={"production": None, "prototype": ["prototypes/**"]},
    )
    return svc


class GateChannel:
    """以真实子进程驱动 mcp_gate.py 的 JSON-RPC(stdio)通道接缝。"""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        full_env = {k: v for k, v in os.environ.items() if k != "MGS_RUNTIME_ROOT"}
        full_env.update(env or {})
        self.proc = subprocess.Popen(
            [sys.executable, "-B", str(GATE_SCRIPT)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=full_env)
        self._id = 0

    def send(self, payload: dict) -> None:
        assert self.proc.stdin
        self.proc.stdin.write((json.dumps(payload) + "\n").encode())
        self.proc.stdin.flush()

    def read_msg(self, timeout: float = 15.0) -> dict | None:
        assert self.proc.stdout
        deadline = time.time() + timeout
        buf = b""
        while time.time() < deadline:
            ready, _, _ = select.select([self.proc.stdout], [], [], 0.2)
            if ready:
                line = self.proc.stdout.readline()
                if not line:
                    return None  # 服务器退出/连接失效
                buf += line
                try:
                    return json.loads(buf.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
        raise TimeoutError("通道响应超时")

    def call(self, method: str, params: dict | None = None) -> dict | None:
        self._id += 1
        payload: dict = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            payload["params"] = params
        self.send(payload)
        return self.read_msg()

    def initialize(self) -> None:
        self.call("initialize", {"protocolVersion": "2025-06-18",
                                 "capabilities": {}})

    def mgs_write(self, token: str, path: str, content: str) -> tuple[dict | None, dict | None]:
        """返回 (原始响应, 解析出的结果 JSON 或 None)。"""
        resp = self.call("tools/call", {"name": "mgs_write", "arguments": {
            "token": token, "path": path, "content": content}})
        if resp is None or "result" not in resp:
            return resp, None
        try:
            parsed = json.loads(resp["result"]["content"][0]["text"])
        except (KeyError, IndexError, json.JSONDecodeError):
            return resp, None
        return resp, parsed

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
