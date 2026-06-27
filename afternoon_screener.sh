#!/bin/bash
# 午后选股刷新 — 工作日 14:00 CST (06:00 UTC) 执行
# 尾盘暴跌后候选池可能完全变化，需要重新扫描

set -e

DOW=$(date -u +%u)
if [ "$DOW" -gt 5 ]; then
    exit 0
fi

LOG="/root/ai_trading_package/quant/quant_scripts/data/afternoon_screener.log"
SCREENER="/root/ai_trading_package/quant/quant_scripts/stock_screener.py"
SAVE="/root/ai_trading_package/quant/quant_scripts/data/screener_top15.json"

echo "[$(date -Iseconds)] 午后选股开始..." >> "$LOG"

PYTHONPATH=/root/ai_trading_package/quant/quant_scripts /usr/local/bin/python3 \
    "$SCREENER" --top 15 --save "$SAVE" >> "$LOG" 2>&1

echo "[$(date -Iseconds)] 完成" >> "$LOG"
