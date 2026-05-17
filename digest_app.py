#!/config/quant_env/bin/python3
"""
工作报告 digest（P3）— 从已落盘 JSON 生成≤400/500字摘要骨架，供 Hermes 润色后推微信。
"""
import json
import os
import sys
from datetime import datetime

DATA = "/config/quant_scripts/data"


def _load(name):
    p = os.path.join(DATA, name)
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def morning_digest():
    m = _load("morning_output.json")
    if not m:
        return {"error": "morning_output.json missing"}
    constraints_fail = [c for c in m.get("constraints", []) if not c.get("pass")]
    cands = (m.get("candidates") or [])[:3]
    lines = [
        f"【早计划】{datetime.now().strftime('%m-%d')}",
        f"建议: {m.get('recommendation', '?')}",
        f"现金: {m.get('cash')} 总资产: {m.get('total_assets')}",
    ]
    if constraints_fail:
        lines.append(f"硬约束: {len(constraints_fail)}项未通过")
    if cands:
        lines.append("关注: " + ", ".join(f"{c.get('code')}" for c in cands))
    qs = m.get("quant_summary") or m.get("quant_per_stock") or {}
    if isinstance(qs, dict) and qs:
        lines.append("量化: 已注入 per_stock/regime")
    text = "\n".join(lines)[:400]
    return {"phase": "digest_morning", "digest_text": text, "needs_hermes": True,
            "instruction": "可微调措辞后作为②工作报告-早计划推微信，≤400字。"}


def night_digest():
    n = _load("night_output.json")
    r = _load("review_bundle.json")
    if not n:
        return {"error": "night_output.json missing"}
    lines = [
        f"【晚复盘】{datetime.now().strftime('%m-%d')}",
        f"收盘建议: {n.get('recommendation', '?')}",
        f"持仓: {len(n.get('holdings') or [])}只",
    ]
    audit = r.get("signal_audit") or {}
    if audit.get("summary"):
        s = audit["summary"]
        lines.append(f"信号: 触发{s.get('triggers',0)} 分析{s.get('analyses',0)}")
    text = "\n".join(lines)[:500]
    return {"phase": "digest_night", "digest_text": text, "review_bundle_path": r.get("review_bundle_path"),
            "needs_hermes": True,
            "instruction": "结合 review 写教训入 stock_kb；润色后作为②晚复盘推微信，≤500字。"}


def main():
    phase = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if phase == "morning":
        out = morning_digest()
    elif phase in ("night", "review"):
        out = night_digest()
    else:
        out = {"error": "usage: digest_app.py morning|night"}
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
