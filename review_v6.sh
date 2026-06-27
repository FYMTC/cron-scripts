#!/bin/bash
# 夜报 v6 — Agent Reach 中美跨市场对比
# 拉取 Twitter/Reddit/雪球 + 对比A股vs美股情绪
set -e

SCRIPT_DIR="$(dirname "$0")"
AGENT_REACH_VENV="$HOME/.agent-reach-venv"

# Step 1: Agent Reach cross-market context
echo "=== AGENT_REACH_NIGHT_CONTEXT ==="
source "$AGENT_REACH_VENV/bin/activate" 2>/dev/null || true
python3 "$SCRIPT_DIR/agent_reach_context.py" night 2>/dev/null || echo '{"error":"agent_reach_fetch_failed"}'
echo "=== END_AGENT_REACH ==="

# Step 2: Market snapshot
echo ""
echo "=== MARKET_SNAPSHOT ==="
cat /config/quant_scripts/market_snapshot.json 2>/dev/null || echo '{"error":"no_snapshot"}'
echo "=== END_SNAPSHOT ==="

# Step 3: Night preflight context
echo ""
echo "=== NIGHT_PREFLIGHT ==="
cat /config/quant_scripts/data/night_preflight_output.json 2>/dev/null || echo '{"status":"not_run"}'
echo "=== END_PREFLIGHT ==="
