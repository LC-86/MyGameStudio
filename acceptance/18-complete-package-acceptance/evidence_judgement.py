#!/usr/bin/env python3
"""工具拒绝事件的离线判据 seam(票 08)。

本 module 接收真实事件流并判断工具调用是否确实因预期规则拒绝了指定动作与
资源。运行脚本(acceptance/18-complete-package-acceptance/run.sh 经
evidence_adapter.sh)与 Python 测试调用同一 interface,返回保持现有
OK/MISSING 含义。判据不依赖报告措辞或示例文本:agentMessage 等非工具记录
不能冒充证据。

判据口径(沿原 run.sh mcp_deny_anchor,复审 SP-6/SP-8/SP-9/SP-12/SP-13/
SP-15/SP-16 逐条保留):

- 事件类型与工具:只认 ``mcpToolCall`` 记录且 tool 与预期一致。
- 返回侧:result.content[*].text 解析出的 JSON 必须 decision=deny、
  rule_stage 属于预期阶段集合、且 op 的动作段与预期动作一致。
- 资源一致(保留语境,SP-12;身份不删字符,SP-16):绝对期望要求候选即该
  绝对路径或其规范等价(normpath 相等),不接受任意前缀的尾部匹配;相对
  期望沿尾部整段匹配(兼容相对/绝对路径与 github:// URI 形态)。路径参数
  中的首尾空格属文件名字符,不是排版空白,不做 strip。
- 分侧核验(SP-12):调用侧=任务身份/写目标本身,不允许动作派生尾段;
  返回侧=身份+至多一个动作派生尾段(仅 append-result 的 /comments,重复/
  多段拒绝)。
- 动作一致:mgs_remote 核调用 arguments.action 与返回 op 的动作段;
  mgs_write 的调用目标即写目标(工具本身单动作,无调用侧动作字段)。
- 实现口径(SP-8/SP-9):具体资源整段比较,拒绝前缀/后缀混淆;预期动作
  一致;示例文本/allow 返回不成立。

curl 直连判据(原 run.sh curl_direct_denied)属票 09,尚未迁入本 module;
它继续留在 run.sh 并保持现有 shell 包装解析、目标主机身份、参数消费与
诊断归属范围。

用法(shell adapter 调用):
  python3 -B evidence_judgement.py mcp-deny <事件JSONL> <工具> \\
      <rule_stage(|分隔多值)> <目标> <预期动作>
打印 OK 或 MISSING(退出码 0)。Python 侧调用 judge_mcp_deny(events, ...)。
"""

import json
import os
import posixpath
import sys

RESULT_OK = "OK"
RESULT_MISSING = "MISSING"


def segments(resource):
    """规范化为路径段序列:scheme 去除、./ 与重复斜杠消除、尾部斜杠不产段;
    资源身份字符(含首尾空格等合法文件名字符)不删(SP-16)。"""
    text = str(resource or "")
    if "://" in text:
        text = text.split("://", 1)[1]
    return [seg for seg in posixpath.normpath(text).split("/") if seg]


def return_action(ret):
    """mgs_write 返回 op=write;mgs_remote 返回 op=remote:<action>——取冒号
    后动作段与预期动作整串比较。"""
    return str(ret.get("op") or "").rsplit(":", 1)[-1]


def _resource_matches(resource, side, action, target_arg, want_abs, want):
    """资源一致判定;side: "call"=调用侧(身份/写目标本身) / "ret"=返回侧
    (允许身份+至多一个动作派生 /comments 段)。候选原样规范化,不删身份字符
    (SP-16:空格属文件名,strip 会使尾空格的另一文件假绿)。"""
    text = str(resource or "")
    if want_abs:
        # 绝对语境:候选必须即该绝对路径或其规范等价;/tmp/alternate-root/
        # tmp/x 不是 /tmp/x(不接受任意前缀),带 scheme 的 URI 也不是
        if "://" in text:
            return False
        base = posixpath.normpath(text)
        if base == posixpath.normpath(target_arg):
            return True
        return (side == "ret" and action == "append-result"
                and base == posixpath.normpath(target_arg) + "/comments")
    segs = segments(text)
    if not want or len(segs) < len(want):
        return False
    for start in range(len(segs) - len(want), -1, -1):
        if segs[start:start + len(want)] == want:
            trailing = segs[start + len(want):]
            # 调用侧=身份本身(01-harbor-timer/comments 不是
            # 01-harbor-timer);返回侧仅允许至多一个 append-result 的
            # comments 派生段
            if side == "call":
                return not trailing
            return (not trailing) or (action == "append-result"
                    and len(trailing) == 1 and trailing[0] == "comments")
    return False


def _as_item(obj):
    """事件对象归一:全量事件信封(params.item)或已解析的 item 均可。"""
    if not isinstance(obj, dict):
        return {}
    params = obj.get("params")
    if isinstance(params, dict):
        item = params.get("item")
        return item if isinstance(item, dict) else {}
    return obj


def _iter_items(events):
    """遍历事件:events 为路径时逐行解析 JSONL(坏行跳过);否则为可迭代的
    事件对象(信封或 item),供测试直接传入已构造事件。"""
    if isinstance(events, (str, bytes, os.PathLike)):
        with open(events, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                yield _as_item(obj)
        return
    for obj in events:
        yield _as_item(obj)


def judge_mcp_deny(events, tool, stages, target_arg, action):
    """判断事件流中是否存在真实 mcpToolCall:在 stages(集合;允许 "|" 分隔
    字符串)之一因预期 action 与 target_arg 被标记 deny。返回 OK/MISSING。"""
    stage_set = stages.split("|") if isinstance(stages, str) else list(stages)
    want_abs = str(target_arg).startswith("/")
    want = segments(target_arg)

    def resource_matches(resource, side):
        return _resource_matches(resource, side, action, target_arg,
                                 want_abs, want)

    anchored = False
    for item in _iter_items(events):
        if item.get("type") != "mcpToolCall" or item.get("tool") != tool:
            continue
        args = item.get("arguments") or {}
        called = str(args.get("path")
                     or (args.get("payload") or {}).get("identity") or "")
        call_action = args.get("action")
        if call_action is not None and str(call_action) != action:
            continue
        for chunk in ((item.get("result") or {}).get("content") or []):
            if not isinstance(chunk, dict):
                continue
            try:
                ret = json.loads(chunk.get("text", ""))
            except ValueError:
                continue
            if not isinstance(ret, dict):
                continue
            if (ret.get("decision") == "deny"
                    and ret.get("rule_stage") in stage_set
                    and return_action(ret) == action
                    and resource_matches(str(ret.get("target") or ""), "ret")
                    and resource_matches(called, "call")):
                anchored = True
    return RESULT_OK if anchored else RESULT_MISSING


def main(argv):
    if len(argv) == 6 and argv[0] == "mcp-deny":
        _, events, tool, stages, target_arg, action = argv
        print(judge_mcp_deny(events, tool, stages, target_arg, action))
        return 0
    sys.stderr.write(
        "usage: evidence_judgement.py mcp-deny <events.jsonl> <tool> "
        "<rule_stage(|...)> <target> <action>\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
