#!/bin/bash
# 盘前简报 v6 — stock_kb + 夜报上下文 + Agent Reach
set -e

SCRIPT_DIR="$(dirname "$0")"
AGENT_REACH_VENV="$HOME/.agent-reach-venv"
PY=/root/ai_trading_package/quant_env/bin/python3
QUANT_DIR="/root/ai_trading_package/quant/quant_scripts"

echo "=== PREV_NIGHT_REPORT (cron_reports 上下文链) ==="
cd "$QUANT_DIR"
$PY daily_context.py load --job "盘前简报" --max-chars 2000 2>/dev/null || echo "(无前置夜报)"

echo ""
echo "=== PORTFOLIO_TRUTH ==="
$PY -c "
from stock_kb import StockKB
import json, sqlite3
kb = StockKB()
t = kb.read_portfolio_truth()
db = sqlite3.connect('$QUANT_DIR/trade_log.db')
cur = db.execute('SELECT * FROM signal_log ORDER BY rowid DESC LIMIT 10')
cols = [c[0] for c in cur.description]
t['recent_signals'] = [dict(zip(cols, r)) for r in cur.fetchall()]
db.close()
print(json.dumps(t, ensure_ascii=False, indent=2))
" 2>&1

echo ""
echo "=== AGENT_REACH_MORNING_CONTEXT ==="
source "$AGENT_REACH_VENV/bin/activate" 2>/dev/null || true
python3 "$SCRIPT_DIR/agent_reach_context.py" morning 2>/dev/null || echo '{"error":"agent_reach_failed"}'
