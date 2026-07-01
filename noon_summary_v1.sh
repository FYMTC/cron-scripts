#!/bin/bash
# 午间总结 v1 — 盘中 LLM 分析报告（T1.12 新增）
# 在 11:30 noon_refresh_app 之后运行，读取 noon_output.json 经 LLM 加工推送
set -e

PY=/root/ai_trading_package/quant_env/bin/python3
QUANT_DIR="/root/ai_trading_package/quant/quant_scripts"

echo "=== NOON_OUTPUT ==="
if [ -f "$QUANT_DIR/data/noon_output.json" ]; then
  $PY -c "
import json
d = json.load(open('$QUANT_DIR/data/noon_output.json'))
# 只输出精华，供 LLM 分析
out = {
    'recommendation': d.get('recommendation'),
    'holdings_summary': [],
    'alerts': d.get('alerts', [])[:5],
    'constraints': [c for c in d.get('constraints', []) if not c.get('pass')][:3],
    'market': d.get('index', {}),
}
for h in (d.get('holdings', []) or []):
    out['holdings_summary'].append({
        'code': h.get('code'), 'name': h.get('name'),
        'price': h.get('price'), 'pct': h.get('change_pct', h.get('gap_pct', 0)),
        'shares': h.get('shares'),
    })
print(json.dumps(out, ensure_ascii=False, indent=2))
" 2>&1
else
  echo '{"error":"noon_output.json not found"}'
fi

echo ""
echo "=== GUARD_LAST_10 ==="
tail -10 "$QUANT_DIR/guard_daemon.log" 2>/dev/null | grep -iE "alert|rapid|surge|异动|急跌|大涨" || echo "(无告警)"

echo ""
echo "=== SIGNAL_RECENT ==="
$PY -c "
import json
d = json.load(open('$QUANT_DIR/guard_config.json'))
signals = d.get('signals', [])
triggered = [s for s in signals if s.get('type') in ('rapid_drop','rapid_surge','price_below','price_above')]
for s in triggered[:8]:
    print(f'{s[\"id\"]} {s[\"code\"]} {s[\"name\"]} {s[\"type\"]} {s.get(\"rationale\",\"\")[:60]}')
" 2>&1
