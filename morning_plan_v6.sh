#!/bin/bash
# 盘前简报 v6 — Agent Reach 全球情绪注入
# 先拉取 Twitter/Reddit/雪球 情绪数据，再输出给 LLM 分析
set -e

SCRIPT_DIR="$(dirname "$0")"
AGENT_REACH_VENV="$HOME/.agent-reach-venv"

# Step 1: Fetch Agent Reach context
echo "=== AGENT_REACH_MORNING_CONTEXT ==="
source "$AGENT_REACH_VENV/bin/activate" 2>/dev/null || true
python3 "$SCRIPT_DIR/agent_reach_context.py" morning 2>/dev/null || echo '{"error":"agent_reach_fetch_failed"}'
echo "=== END_AGENT_REACH ==="

# Step 2: Fetch market snapshot (existing pipeline)
echo ""
echo "=== MARKET_SNAPSHOT ==="
cat /root/ai_trading_package/quant/quant_scripts/market_snapshot.json 2>/dev/null || echo '{"error":"no_snapshot"}'
echo "=== END_SNAPSHOT ==="
