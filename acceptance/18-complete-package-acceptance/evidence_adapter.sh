# 票 08:验收判据的 Shell 适配层。
#
# 运行脚本(acceptance/18-complete-package-acceptance/run.sh)与离线测试共用
# 同一判据 module(evidence_judgement.py);适配器只做参数传递与 OK/MISSING
# 返回,不再内含判据实现,测试因此无需正则截取 Shell 函数源码即可验证同一
# 判据。curl 直连判据属票 09,迁入前仍留在 run.sh 并保持现有解析范围。
MGS_EVIDENCE_JUDGE="${MGS_EVIDENCE_JUDGE:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/evidence_judgement.py}"

mcp_deny_anchor() { # mcp_deny_anchor <事件JSONL> <工具> <rule_stage(|分隔多值)> <目标> <预期动作>
  python3 -B "$MGS_EVIDENCE_JUDGE" mcp-deny "$@"
}
