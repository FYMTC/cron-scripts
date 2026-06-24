#!/bin/bash
# Agent Desk 交易时段轮询 — 每 5 分钟由 cron 触发
# 仅在 A 股交易时段内执行：工作日 09:30-15:00 CST = 01:30-07:00 UTC
# 午休 11:30-13:00 CST = 03:30-05:00 UTC 跳过

set -e

HOUR=$(date -u +%H)
MINUTE=$(date -u +%M)
DOW=$(date -u +%u)  # 1=Mon .. 5=Fri, 6=Sat, 7=Sun

# 周末不跑
if [ "$DOW" -gt 5 ]; then
    exit 0
fi

TOTAL_MINUTES=$((10#$HOUR * 60 + 10#$MINUTE))

# 盘前不跑 (< 01:30 UTC)
if [ "$TOTAL_MINUTES" -lt 90 ]; then
    exit 0
fi

# 收盘后不跑 (> 07:00 UTC)
if [ "$TOTAL_MINUTES" -gt 420 ]; then
    exit 0
fi

# 午休不跑 (03:30-05:00 UTC = 210-300 min)
if [ "$TOTAL_MINUTES" -gt 210 ] && [ "$TOTAL_MINUTES" -lt 300 ]; then
    exit 0
fi

PYTHONPATH=/config/quant_scripts /usr/local/bin/python3 /config/.hermes/scripts/agent_desk_poll_app.py
