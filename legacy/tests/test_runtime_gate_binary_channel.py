#!/usr/bin/env python3
"""受控写入的二进制载荷与 mgs-gate 通道参数校验。

任务票 12 从 tests/test_runtime_gate.py 的原始总入口按真实行为主题拆出;
每条 check 的条件、消息与断言对象与原案例逐字一致(任务票 11 的二进制
载荷、任务票 12 的通道参数校验),仅重组位置。原总入口仍聚合本主题。本
主题可直接运行:

    python3 -B tests/test_runtime_gate_binary_channel.py
"""

import base64
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

from runtime_gate_support import make_checker, mcp_gate, new_instance, run_theme, setup_service

FAILURES, check = make_checker()


def test_binary_payload() -> None:
    """案例 19:音频等非文本资源以字节载荷经受控通道,语义与文本写入一致。"""

    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-bin-"))
    try:
        svc, project = setup_service(root)
        code = project / "src/player.js"

        # 19. 二进制资源写入(任务票 11):音频等非文本资源以字节载荷经受控通道。
        #     语义与文本写入一致:同一授权交集、同一字节级版本校验与审计。
        wav = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00" + bytes(range(256))
        xid, xtok = new_instance(svc, "implement",
                                 ["assets/audio/**",
                                  "docs/mygamestudio/work/01-status/results/**"],
                                 task="T-audio")
        res = svc.write(xtok, "assets/audio/warning.wav", data=wav,
                        note="预警音二进制写入")
        check(res["decision"] == "allow", f"二进制资源写入应成功,实际 {res}")
        audio_path = project / "assets/audio/warning.wav"
        check(audio_path.read_bytes() == wav, "二进制文件字节应逐字节一致(非 UTF-8 也能落盘)")
        check(res["bytes"] == len(wav)
              and res["written_sha256"] == hashlib.sha256(wav).hexdigest(),
              f"审计口径应按字节记录大小与哈希,实际 {res.get('bytes'), res.get('written_sha256')}")
        # 基于字节的版本校验对二进制同样生效
        res = svc.write(xtok, "assets/audio/warning.wav", data=wav + b"\x00",
                        expected_sha256=hashlib.sha256(wav).hexdigest())
        check(res["decision"] == "allow", f"字节级版本匹配的二进制更新应成功,实际 {res}")
        check(audio_path.read_bytes() == wav + b"\x00", "二进制更新应写入新字节")
        # 越界二进制同样被拒,目标字节不变
        before = code.read_bytes()
        res = svc.write(xtok, "src/player.js", data=b"\x89PNG\r\n\x1a\n")
        check(res["decision"] == "deny" and res["rule_stage"] in ("role_scope", "task_grant"),
              f"任务授权外的二进制写入应被拒,实际 {res}")
        check(code.read_bytes() == before, "被拒后目标字节应保持不变")
        svc.release_instance(xid)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_channel_payload_validation() -> None:
    """案例 20:content 与 content_base64 恰一,非法载荷按通道参数错误失效闭合。"""

    root = Path(tempfile.mkdtemp(prefix="mgs02-gate-chan-"))
    try:
        svc, project = setup_service(root)
        wav = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00" + bytes(range(256))

        # 20. mgs-gate 通道参数校验(任务票 11):content 与 content_base64 恰一,
        #     非法 base64 与缺失载荷都按通道参数错误失效闭合,不落盘。
        def gate_call(args: dict) -> dict:
            payload = mcp_gate.handle_tools_call(svc, "mgs_write", args)
            return json.loads(payload["content"][0]["text"])

        yid, ytok = new_instance(svc, "implement", ["assets/audio/**"], task="T-b64")
        res = gate_call({"token": ytok, "path": "assets/audio/x.wav",
                         "content": "x", "content_base64": base64.b64encode(b"x").decode()})
        check(res["decision"] == "deny" and res["rule_stage"] == "channel",
              f"content 与 content_base64 同时提供应按通道参数错误拒绝,实际 {res}")
        res = gate_call({"token": ytok, "path": "assets/audio/x.wav"})
        check(res["decision"] == "deny" and res["rule_stage"] == "channel",
              f"载荷完全缺失应按通道参数错误拒绝,实际 {res}")
        check(not (project / "assets/audio/x.wav").exists(),
              "参数错误的调用不得落盘")
        res = gate_call({"token": ytok, "path": "assets/audio/x.wav",
                         "content_base64": "!!not-base64!!"})
        check(res["decision"] == "deny" and res["rule_stage"] == "channel",
              f"非法 base64 应按通道参数错误拒绝,实际 {res}")
        # 命令行 base64 工具的换行折行被容忍(剥掉空白后严格解码)
        wrapped = base64.encodebytes(wav)  # 每 76 字符折行,含换行
        check(b"\n" in wrapped, "encodebytes 应产生带换行的折行输出")
        res = gate_call({"token": ytok, "path": "assets/audio/wrapped.wav",
                         "content_base64": wrapped.decode()})
        check(res["decision"] == "allow", f"带换行折行的 base64 载荷应被接受,实际 {res}")
        check((project / "assets/audio/wrapped.wav").read_bytes() == wav,
              "折行 base64 写入的字节应与原字节一致")
        res = gate_call({"token": ytok, "path": "assets/audio/ok.wav",
                         "content_base64": base64.b64encode(wav).decode(),
                         "note": "通道侧 base64 载荷"})
        check(res["decision"] == "allow", f"通道侧 base64 载荷写入应成功,实际 {res}")
        check((project / "assets/audio/ok.wav").read_bytes() == wav,
              "通道侧 base64 写入的字节应与原字节一致")
        svc.release_instance(yid)
    finally:
        shutil.rmtree(root, ignore_errors=True)


TESTS = (test_binary_payload, test_channel_payload_validation)

if __name__ == "__main__":
    sys.exit(run_theme("受控写入二进制载荷与通道参数校验", TESTS, FAILURES))
