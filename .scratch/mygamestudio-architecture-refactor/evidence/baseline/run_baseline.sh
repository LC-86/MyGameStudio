#!/bin/sh
# 票 01 基线总入口(薄封装)。可复跑;全部离线,零真实模型/网络/远端写入。
#
#   ./run_baseline.sh
#
# 结果写入本目录 results/baseline.json 与 BASELINE-REPORT.md。
set -e
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 -B "$HERE/run_baseline.py" "$@"
