#!/bin/bash
# 夜报 v6 — 保留原 review_app.py 全流程 + Agent Reach 跨市场补充
set -e

SCRIPT_DIR="$(dirname "$0")"
AGENT_REACH_VENV="$HOME/.agent-reach-venv"
QUANT_DIR="/root/ai_trading_package/quant/quant_scripts"
DATA_DIR="$QUANT_DIR/data"

echo "=== STEP 1: review_app.py (原 v5 全流程) ==="
# Run the original review_app to generate review_bundle.json
cd "$QUANT_DIR"
/root/ai_trading_package/quant_env/bin/python3 "$SCRIPT_DIR/review_app.py" 2>&1 || echo "WARN: review_app had errors"

echo ""
echo "=== STEP 2: review_bundle.json ==="
cat "$DATA_DIR/review_bundle.json" 2>/dev/null || echo '{"error":"review_bundle not generated"}'

echo ""
echo "=== STEP 3: night_output.json ==="
cat "$DATA_DIR/night_output.json" 2>/dev/null || echo '{"status":"not_generated"}'

echo ""
echo "=== STEP 4: AGENT_REACH_NIGHT_CONTEXT ==="
source "$AGENT_REACH_VENV/bin/activate" 2>/dev/null || true
python3 "$SCRIPT_DIR/agent_reach_context.py" night 2>/dev/null || echo '{"error":"agent_reach_fetch_failed"}'
