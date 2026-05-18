#!/config/quant_env/bin/python3
"""
盘前 Plan 薄封装（P2）：morning_app + 组合/标的量化上下文 + auto_generate + 工作报告 digest。
"""
import json
import os
import subprocess
import sys

VENV_PY = "/config/quant_env/bin/python3"
SCRIPTS = "/config/quant_scripts"
MORNING = "/config/quant_scripts/apps/morning.py"
SIGNAL_LOOP = "/config/quant_scripts/signal_loop.py"
DIGEST = os.path.join(os.path.dirname(__file__), "digest_app.py")
OUT = "/config/quant_scripts/data/morning_output.json"
PLAN_JSON = "/config/quant_scripts/data/plan_bundle.json"


def _portfolio_quant(holdings: list, limit: int = 5) -> dict:
    sys.path.insert(0, SCRIPTS)
    out = {"per_stock": {}}
    try:
        import numpy as np
        from market_regime import fetch_index_data, fit_hmm

        closes = fetch_index_data("000300", days=500)
        if closes is not None and len(closes) > 30:
            log_returns = np.diff(np.log(closes))
            out["market_regime"] = fit_hmm(log_returns) or {}
        else:
            out["market_regime_error"] = "index_data_unavailable"
    except Exception as e:
        out["market_regime_error"] = str(e)[:120]
    try:
        from tradingagents_runner import fetch_quant_context

        for h in (holdings or [])[:limit]:
            code = h.get("code")
            if not code:
                continue
            ctx = fetch_quant_context(code)
            out["per_stock"][code] = (ctx[:2000] if isinstance(ctx, str) else str(ctx)[:2000])
    except Exception as e:
        out["fetch_quant_context_error"] = str(e)[:200]
    return out


def _run_digest() -> dict:
    r = subprocess.run([VENV_PY, DIGEST, "morning"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout or "digest failed")[:300]}
    raw = (r.stdout or "").strip()
    brace = raw.find("{")
    if brace >= 0:
        return json.loads(raw[brace:])
    return json.loads(raw)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    r1 = subprocess.run(
        [VENV_PY, MORNING, "--save", OUT],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if r1.returncode != 0:
        sys.stderr.write(r1.stderr or "")
        sys.exit(r1.returncode)

    morning = {}
    if os.path.isfile(OUT):
        with open(OUT, encoding="utf-8") as f:
            text = f.read()
        brace = text.find("{")
        if brace >= 0:
            morning = json.loads(text[brace:])
        else:
            morning = json.loads(text)

    quant_bundle = _portfolio_quant(morning.get("holdings") or [])

    r2 = subprocess.run(
        [VENV_PY, SIGNAL_LOOP, "auto-generate"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    sig = {}
    if r2.stdout:
        try:
            sig = json.loads(r2.stdout)
        except json.JSONDecodeError:
            sig = {"raw": r2.stdout[:1000]}

    digest = _run_digest()

    plan = {
        "generated_at": morning.get("generated_at"),
        "phase": "plan",
        "morning_output_path": OUT,
        "recommendation": morning.get("recommendation"),
        "constraints_failed": [c for c in morning.get("constraints", []) if not c.get("pass")],
        "candidates_top": (morning.get("candidates") or [])[:5],
        "event_risk": morning.get("event_risk"),
        "de_risk_plan": morning.get("de_risk_plan"),
        "quant_bundle": quant_bundle,
        "signal_auto_generate": sig,
        "digest": digest,
        "wechat_work_report_body": digest.get("wechat_work_report_body") or digest.get("digest_text", ""),
        "push_wechat_required": bool(digest.get("push_wechat_required", True)),
        "wechat_report_type": digest.get("wechat_report_type", "②工作报告-早计划"),
        "needs_hermes": True,
        "instruction": digest.get(
            "instruction",
            "必读 wechat_work_report_body；润色扩展后作为最终回复推微信（deliver=origin）。禁止跳过 digest。",
        ),
    }
    with open(PLAN_JSON, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    plan["plan_bundle_path"] = PLAN_JSON
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
