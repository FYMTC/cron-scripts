#!/bin/bash
# 夜报 v6 — 从 stock_kb + guard_log + market_snapshot + Agent Reach 直接生成
set -e

SCRIPT_DIR="$(dirname "$0")"
AGENT_REACH_VENV="$HOME/.agent-reach-venv"
PY=/root/ai_trading_package/quant_env/bin/python3
QUANT_DIR="/root/ai_trading_package/quant/quant_scripts"

echo "=== STEP 1: PORTFOLIO_TRUTH ==="
$PY -c "
from stock_kb import StockKB
import json
kb = StockKB()
t = kb.read_portfolio_truth()
# Add today's trades
import sqlite3
db = sqlite3.connect('$QUANT_DIR/trade_log.db')
cur = db.execute(\"SELECT trade_date, action, stock_code, price, shares, amount FROM stock_trades WHERE trade_date LIKE '$(date +%Y-%m-%d)%' ORDER BY created_at DESC\")
trades = [dict(zip(['date','action','code','price','shares','amount'], r)) for r in cur.fetchall()]
t['today_trades'] = trades
# Add recent signals
cur2 = db.execute(\"SELECT * FROM signal_log ORDER BY rowid DESC LIMIT 20\")
cols = [c[0] for c in cur2.description]
signals = [dict(zip(cols, r)) for r in cur2.fetchall()]
t['recent_signals'] = [s for s in signals if '$(date +%Y-%m-%d)' in str(s.get('created_at',''))][:10]
db.close()
print(json.dumps(t, ensure_ascii=False, indent=2))
" 2>&1

echo ""
echo "=== STEP 2: GUARD_ALERTS (last 50 lines) ==="
tail -50 "$QUANT_DIR/guard_daemon.log" 2>/dev/null | grep -iE "alert|signal|异动|急跌|大涨|推送|唤醒|热加载" || echo "(无今日告警)"

echo ""
echo "=== STEP 3: AGENT_REACH_NIGHT_CONTEXT ==="
source "$AGENT_REACH_VENV/bin/activate" 2>/dev/null || true
python3 "$SCRIPT_DIR/agent_reach_context.py" night 2>/dev/null || echo '{"error":"agent_reach_failed"}'
