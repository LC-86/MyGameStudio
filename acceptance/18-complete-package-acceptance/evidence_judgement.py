#!/usr/bin/env python3
"""验收事件的离线判据 seam(票 08 工具拒绝 + 票 09 直连失败)。

本 module 接收真实事件流并判断工具调用/命令执行是否确实构成预期证据。
运行脚本(acceptance/18-complete-package-acceptance/run.sh 经
evidence_adapter.sh)与 Python 测试调用同一 interface,返回保持现有
OK/MISSING 含义。判据不依赖报告措辞或示例文本:agentMessage 等非工具记录
不能冒充证据。

两类判据:

- ``judge_mcp_deny``(票 08,沿原 run.sh mcp_deny_anchor,复审
  SP-6/SP-8/SP-9/SP-12/SP-13/SP-15/SP-16):只认 ``mcpToolCall`` 记录,
  核对 tool、返回 decision=deny/rule_stage/op 动作段、调用与返回两侧资源
  身份和预期动作。资源一致规则:绝对期望要求候选即该绝对路径或其规范等价
  (normpath 相等),不接受任意前缀;相对期望沿尾部整段匹配。路径参数中的
  首尾空格属文件名字符,不做 strip。分侧核验:调用侧=任务身份/写目标本身,
  不允许动作派生尾段;返回侧=身份+至多一个动作派生尾段(仅 append-result
  的 /comments)。
- ``judge_curl_direct_denied``(票 09,沿原 run.sh curl_direct_denied,复审
  SP-13/15/18~30):只认 ``commandExecution`` 记录。实际执行的命令剥 shell
  包装后首个可执行 token 为 curl、恰一个 URL 形态位置参数的 urlparse 主机
  为替身地址 127.0.0.1、执行失败且原始输出含绑定替身主机的 curl 连接诊断
  行。名单外旗标、改变连接语义的旗标、重定向、重试、glob 等形态保守拒绝;
  不实现完整 shell/curl 解释器(支持范围与已接受限制保持)。

用法(shell adapter 调用):
  python3 -B evidence_judgement.py mcp-deny <事件JSONL> <工具> \\
      <rule_stage(|分隔多值)> <目标> <预期动作>
  python3 -B evidence_judgement.py curl-direct-deny <事件JSONL>
打印 OK 或 MISSING(退出码 0)。Python 侧调用
judge_mcp_deny(events, ...) / judge_curl_direct_denied(events)。
"""

import json
import os
import posixpath
import re
import shlex
import sys
from urllib.parse import urlparse

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


# —— curl 直连判据(票 09 自 run.sh curl_direct_denied 迁入)—— 
# 失败证据须能证明「对替身的连接未被允许」(SP-23/SP-25/SP-26):
# 可接受记录约束为 curl 诊断行形态——错误前缀 curl: (7|28)+连接
# 短语+目标主机(SP-25,区分连接阶段与响应阶段);诊断行中捕获的
# 主机 token 与替身 127.0.0.1 相等比较(SP-26,非子串包含)。通用
# operation timed out / 响应阶段超时(连接已成功、部分字节已到达)
# 不再单独成立;响应正文中的连接措辞(无诊断前缀)不成立;隐式
# ambient 配置使实连他址的失败输出点名他址,同样不能成立。残余
# 边界:正文若逐字节模拟完整诊断行,aggregatedOutput 不分 stdout/
# stderr,单正则不能普遍保证来源(审方明示),留档不宣称完备。
# 报告措辞中文词族不再独立成立
connect_diag = re.compile(
    r"^curl: \((?:7|28)\) (?:Failed to connect to|Couldn't connect to) "
    r"(?P<host>\S+?)(?: |:)",
    re.IGNORECASE)
STANDBY_HOST = "127.0.0.1"
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
# 已知 curl 旗标形态(固定探针调用口径):带值旗标吃掉其后一个参数,
# 无值旗标(可聚合,如 -sS)直接跳过;名单外旗标保守拒绝。改变连接
# 语义的旗标不在名单内:长参数 --proxy/--resolve/--host/--interface
# (SP-18)与短旗标同义形态 -x(代理)/-K(配置文件,文件内可再设
# proxy/resolve/connect-to 等改变连接语义项)/-U(代理凭据,代理域
# 旗标、固定探针从不用,宁严勿宽一并移除,SP-20)都会使实际连接
# 目标/绑定偏离 URL,固定探针不核验其效果,出现即整个命令不成立
# (返回 None);--noproxy 是禁止代理、保持直连语义,固定探针自身
# 在用,保留。重定向旗标 -L/--location 同口径保守拒绝(SP-21):
# curl 跟随 302 后判据无法确认最终目标归属——.1 被直连访问、转向
# .2 连接失败也会冒充初始目标被拒。短旗标带值/无值按本机 curl 语义
# 核对(SP-27):g(globoff)/J(remote-header-name)/Z(parallel) 均为无值,
# 列入 CURL_PLAIN_SHORT——旧表把三者当带值会吞掉首个或唯一 URL。
# --retry 保守拒绝(SP-28):固定探针不实现逐次尝试证明,出现即整个
# 命令不成立;真失败+重试的对照随之 MISSING,属已披露取舍。上传值
# glob 保守拒绝(SP-30):-T/--upload-file 的值(分离/粘连/聚合内粘连
# 均按 SP-22 语义取值)含 {}[] 任一字符即整个命令不成立;不实现
# curl 上传 glob 解析器。集合沿原实现用 set((...)) 构造,保持迁移
# 前后的判据口径与构造逐字一致(原为 heredoc 内不出现顶格 } 便于
# 整体提取)。
CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzD")
CURL_PLAIN_SHORT = set("sSkvIifnN46qgJZ")
CURL_VALUE_LONG = set((
    "--header", "--max-time", "--request", "--data", "--data-raw",
    "--data-binary", "--output", "--user-agent", "--user", "--write-out",
    "--cookie", "--connect-timeout", "--noproxy", "--url",
    "--form", "--upload-file", "--cert", "--key", "--cacert",
))
CURL_PLAIN_LONG = set((
    "--version", "--silent", "--show-error", "--insecure",
    "--verbose", "--head", "--fail", "--compressed", "--no-buffer",
    "--progress-bar", "--ipv4", "--ipv6", "--http1.1", "--http2",
))


def executed_tokens(command):
    # 剥 shell 包装(按位置,SP-13):-c 类短旗标必须紧跟 shell 可执行
    # 之后,其下一个参数才是实际执行的命令体;首个参数是脚本路径或
    # 其他旗标形态即停止解析——sh script.sh -c '…' 的 -c 与命令体只是
    # 脚本参数,shell 实际执行的是脚本本身,未执行 -c 命令体
    text = str(command or "")
    for _ in range(3):
        try:
            tokens = shlex.split(text)
        except ValueError:
            return None
        if not tokens:
            return None
        if os.path.basename(tokens[0]) in SHELLS:
            if len(tokens) < 3:
                return None
            flag = tokens[1]
            if not (flag.startswith("-") and not flag.startswith("--")
                    and "c" in flag[1:]):
                return None
            text = tokens[2]
            continue
        return tokens
    return None


def url_targets(tokens):
    # 解析 curl 参数,收集 URL 形态的连接目标(位置参数):-H 头部值、
    # 注释词串等不是实际连接目标;遇名单外旗标返回 None(保守拒绝,
    # 不能证明执行的形态——如 curl --version; printf … 后接注释)
    args = tokens[1:]
    urls = []
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == "--":
            # URL glob 形态保守拒绝(SP-29):花括号/方括号展开会把一个
            # 位置参数变成多次请求,len(urls)==1 不能证明单请求
            if any(any(ch in arg for ch in "{}[]") for arg in args[i + 1:]):
                return None
            urls.extend(args[i + 1:])
            break
        if tok.startswith("--"):
            if tok in CURL_VALUE_LONG:
                # 上传文件名 glob 保守拒绝(SP-30):--upload-file 的值
                # 含花括号/方括号会把单 URL 展成多次 PUT,len(urls)==1
                # 不能证明单请求;缺值同样不能证明执行形态
                if tok == "--upload-file" and (i + 1 >= len(args) or any(ch in args[i + 1] for ch in "{}[]")):
                    return None
                i += 2
                continue
            if tok in CURL_PLAIN_LONG:
                i += 1
                continue
            return None
        if tok.startswith("-") and len(tok) > 1:
            body = tok[1:]
            # 短旗标值按 curl 语义消费(SP-22):首个带值字符位于 token
            # 末尾(如 -m、-sSm)取下一参数为值;位于中间即粘连形式
            # (-m2、-sSm2)值即 token 余部、只消费当前 token——URL 计数
            # 须反映真实参数语义(旧实现凡含带值字符即 i+=2,-m2 把下一
            # 参数·首 URL·当值吞掉,单 URL 限制被绕过;值字符不在末尾
            # 的歧义形态如 -ms2 按 curl 真实行为取余部为值,留档票面)。
            # 按顺序验证(SP-24):首个带值字符之前的每个字符必须都在
            # CURL_PLAIN_SHORT 内,否则整个命令不成立——禁用前缀 L/K
            # 藏在带值字符前(-Lm2/-LsSm2/-Lm 2/-K路径)不再被跳过;
            # 正常聚合 -sSm2/-sSm 2 前缀均属白名单,消费语义不变
            value_at = next((j for j, ch in enumerate(body)
                             if ch in CURL_VALUE_SHORT), None)
            if value_at is not None:
                if not all(ch in CURL_PLAIN_SHORT for ch in body[:value_at]):
                    return None
                # 上传文件名 glob 保守拒绝(SP-30):短旗标 T 的值按
                # SP-22 语义取值——位于 token 末尾取下一参数,粘连
                # (含聚合 -sST{a,b})取 token 余部
                if body[value_at] == "T":
                    value = args[i + 1] if value_at == len(body) - 1 and i + 1 < len(args) else body[value_at + 1:]
                    if any(ch in value for ch in "{}[]"):
                        return None
                i += 2 if value_at == len(body) - 1 else 1
                continue
            if all(ch in CURL_PLAIN_SHORT for ch in body):
                i += 1
                continue
            return None
        if any(ch in tok for ch in "{}[]"):
            return None
        urls.append(tok)
        i += 1
    return urls


def judge_curl_direct_denied(events):
    """判断事件流中是否存在真实 commandExecution:命令(剥 shell 包装后)
    首个可执行 token 为 curl、实际连接目标参数解析后的主机为替身地址
    127.0.0.1、执行失败且原始输出含绑定替身主机的 curl 连接诊断行。返回
    OK/MISSING。口径沿原 run.sh curl_direct_denied(SP-13/15/18~30 逐条
    保留,名单外旗标/改连接语义旗标/重定向/重试/glob 保守拒绝)。"""
    anchored = False
    for item in _iter_items(events):
        if item.get("type") != "commandExecution":
            continue
        tokens = executed_tokens(item.get("command"))
        if not tokens or os.path.basename(tokens[0]) != "curl":
            continue
        urls = url_targets(tokens)
        if urls is None:
            continue
        if not urls or not all(u.startswith(("http://", "https://")) for u in urls):
            continue
        # 只接受恰好一个 URL 形态位置参数(SP-19):多 URL 命令的整次进程
        # 退出码与合并输出无法把失败归属到目标 URL——目标已返回 200 而另
        # 一 URL 超时(整进程 exit 28)也会被误判为替身直连失败
        if len(urls) != 1:
            continue
        # 127.0.0.1 必须是解析后的实际连接主机(SP-15):唯一 URL 形态位置
        # 参数的 urlparse hostname 恰为 127.0.0.1——userinfo 段
        # (http://127.0.0.1:端口@host)是凭证不是连接目标,域名伪装与
        # IPv6 其他目标同样不成立;无法解析的 URL 形态保守不成立
        def host_is_standby(u):
            try:
                return urlparse(u).hostname == "127.0.0.1"
            except ValueError:
                return False
        if not host_is_standby(urls[0]):
            continue
        failed = (item.get("status") == "failed"
                  or item.get("exitCode") not in (None, 0))
        # 失败证据须为 curl 诊断行且目标主机身份绑定替身(SP-23/25/26):
        # 证明对替身的连接未被允许——连接已成功、响应阶段超时的输出
        # 无诊断行前缀;响应正文中的连接措辞无 curl: (N) 前缀;实连他址
        # 的诊断行捕获主机不等于 127.0.0.1(127.0.0.10 含子串 .1 不再
        # 绑定)。留存 g1 真实输出 curl: (7) Failed to connect to
        # 127.0.0.1 port … 诊断行形态天然满足
        output = str(item.get("aggregatedOutput") or "")
        def diagnostic_binds_standby(line):
            m = connect_diag.search(line)
            return m is not None and m.group("host") == STANDBY_HOST
        if failed and any(diagnostic_binds_standby(line)
                          for line in output.splitlines()):
            anchored = True
    return RESULT_OK if anchored else RESULT_MISSING


def main(argv):
    if len(argv) == 6 and argv[0] == "mcp-deny":
        _, events, tool, stages, target_arg, action = argv
        print(judge_mcp_deny(events, tool, stages, target_arg, action))
        return 0
    if len(argv) == 2 and argv[0] == "curl-direct-deny":
        print(judge_curl_direct_denied(argv[1]))
        return 0
    sys.stderr.write(
        "usage: evidence_judgement.py mcp-deny <events.jsonl> <tool> "
        "<rule_stage(|...)> <target> <action>\n"
        "       evidence_judgement.py curl-direct-deny <events.jsonl>\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
