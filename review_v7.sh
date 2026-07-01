#!/bin/bash
# 夜报 v7 — 通过 webhook 直推，不依赖微信会话
set -e

WEBHOOK_URL="${WECHAT_WEBHOOK_URL:-}"
if [ -z "$WEBHOOK_URL" ]; then
  if [ -f /root/.hermes/env ]; then
    WEBHOOK_URL=$(grep 'WECHAT_WEBHOOK_URL=' /root/.hermes/env | cut -d= -f2-)
  fi
fi

if [ -z "$WEBHOOK_URL" ]; then
  echo "NO WEBHOOK"
  exit 1
fi

SCRIPT_DIR="$(dirname "$0")"
AGENT_REACH_VENV="$HOME/.agent-reach-venv"
PY=/root/ai_trading_package/quant_env/bin/python3
QUANT_DIR="/root/ai_trading_package/quant/quant_scripts"

# ── Step 1: 持仓真相 ──
PORTFOLIO=$($PY -c "
from stock_kb import StockKB
import json, sqlite3
kb = StockKB()
t = kb.read_portfolio_truth()
db = sqlite3.connect('$QUANT_DIR/trade_log.db')
cur = db.execute(\"SELECT trade_date, action, stock_code, price, shares, amount FROM stock_trades WHERE trade_date LIKE '$(date +%Y-%m-%d)%' ORDER BY created_at DESC\")
trades = [dict(zip(['date','action','code','price','shares','amount'], r)) for r in cur.fetchall()]
t['today_trades'] = trades
cur2 = db.execute(\"SELECT * FROM signal_log ORDER BY rowid DESC LIMIT 20\")
cols = [c[0] for c in cur2.description]
signals = [dict(zip(cols, r)) for r in cur2.fetchall()]
t['recent_signals'] = [s for s in signals if '$(date +%Y-%m-%d)' in str(s.get('created_at',''))][:10]
db.close()
print(json.dumps(t, ensure_ascii=False, indent=2)[:3000])
" 2>&1)

# ── Step 2: 告警 ──
ALERTS=$(tail -50 "$QUANT_DIR/guard_daemon.log" 2>/dev/null | grep -iE "alert|rapid|surge|异动|急跌|大涨" | tail -20 || echo "(无)")

# ── Step 3: Agent Reach ──
AGENT_REACH=""
source "$AGENT_REACH_VENV/bin/activate" 2>/dev/null || true
AGENT_REACH=$(python3 "$SCRIPT_DIR/agent_reach_context.py" night 2>/dev/null || echo '{"error":"agent_reach_failed"}')

# ── Step 4: 收盘数据 ──
CLOSE_DATA=""
if [ -f "$QUANT_DIR/data/close_output.json" ]; then
  CLOSE_DATA=$($PY -c "
import json
d=json.load(open('$QUANT_DIR/data/close_output.json'))
out={'recommendation':d.get('recommendation'),'alerts':d.get('alerts',[])[:5],'constraints_failed':[c for c in d.get('constraints',[]) if not c.get('pass')][:3]}
print(json.dumps(out, ensure_ascii=False, indent=2))
" 2>&1)
fi

# ── 组装 LLM 上下文 ──
CONTEXT=$(cat <<EOF
=== 持仓 ===
$PORTFOLIO

=== 今日告警 ===
$ALERTS

=== 盘后数据 ===
$CLOSE_DATA

=== 海外动态 ===
$AGENT_REACH
EOF
)

# ── 输出 ──
echo "$CONTEXT" | head -5000
