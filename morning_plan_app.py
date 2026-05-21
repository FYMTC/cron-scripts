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
FEATURE_SNAPSHOT = "/config/quant_scripts/feature_snapshot.py"
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


def _run_feature_snapshot() -> dict:
    r = subprocess.run([VENV_PY, FEATURE_SNAPSHOT, "--json"], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout or "feature_snapshot failed")[:500]}
    raw = (r.stdout or "").strip()
    brace = raw.find("{")
    if brace >= 0:
        return json.loads(raw[brace:])
    return json.loads(raw)


def _constraint_explainability(constraints: list) -> dict:
    try:
        sys.path.insert(0, SCRIPTS)
        from decision_explainer import build_counterfactual_from_constraints

        return build_counterfactual_from_constraints(constraints or [])
    except Exception as e:
        return {"summary": f"constraint explainability unavailable: {str(e)[:120]}"}


def _build_model_risk_ledger(feature_snapshot: dict, quant_bundle: dict, signal_auto_generate: dict, generated_at: str, event_risk: dict) -> dict:
    feature_runtime = (feature_snapshot or {}).get("runtime_flags") or {}
    portfolio = (feature_snapshot or {}).get("portfolio") or {}
    event_risk_snapshot = portfolio.get("event_risk") or {}
    items = [
        {
            "name": "feature_snapshot",
            "type": "feature_bundle",
            "source_modules": (feature_snapshot or {}).get("source_modules") or [],
            "as_of": (feature_snapshot or {}).get("generated_at"),
            "version": (feature_snapshot or {}).get("as_of_date"),
            "status": "ok" if feature_runtime.get("feature_fresh", True) else "fallback",
            "degraded": not bool(feature_runtime.get("feature_fresh", True)),
            "fallback_reason": None if feature_runtime.get("feature_fresh", True) else "feature_snapshot_stale",
        },
        {
            "name": "market_regime",
            "type": "risk_model",
            "source_modules": ["market_regime"],
            "as_of": (feature_snapshot or {}).get("generated_at"),
            "version": "portfolio.market_regime",
            "status": "ok" if (portfolio.get("market_regime") or {}).get("ok") else "fallback",
            "degraded": not bool((portfolio.get("market_regime") or {}).get("ok")),
            "fallback_reason": None if (portfolio.get("market_regime") or {}).get("ok") else (quant_bundle.get("market_regime_error") or "market_regime_unavailable"),
        },
        {
            "name": "event_risk",
            "type": "risk_overlay",
            "source_modules": ["event_risk"],
            "as_of": (event_risk or {}).get("assessed_at") or (feature_snapshot or {}).get("generated_at"),
            "version": (event_risk or {}).get("date") or (feature_snapshot or {}).get("as_of_date"),
            "status": "fallback" if event_risk_snapshot.get("source") == "not_wired_yet" else "ok",
            "degraded": event_risk_snapshot.get("source") == "not_wired_yet",
            "fallback_reason": "not_wired_yet" if event_risk_snapshot.get("source") == "not_wired_yet" else None,
        },
        {
            "name": "signal_auto_generate",
            "type": "signal_engine",
            "source_modules": ["signal_loop"],
            "as_of": generated_at,
            "version": signal_auto_generate.get("lineage_id") or "plan_bundle.signal_auto_generate",
            "status": "ok" if signal_auto_generate.get("feature_snapshot_used") else "fallback",
            "degraded": not bool(signal_auto_generate.get("feature_snapshot_used")),
            "fallback_reason": None if signal_auto_generate.get("feature_snapshot_used") else "feature_snapshot_not_consumed",
        },
    ]
    degraded_items = [item["name"] for item in items if item.get("degraded")]
    return {
        "summary": {
            "model_count": len(items),
            "degraded_count": len(degraded_items),
            "degraded_items": degraded_items,
            "feature_snapshot_fresh": bool(feature_runtime.get("feature_fresh", True)),
        },
        "items": items,
    }


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
    feature_snapshot = _run_feature_snapshot()

    r2 = subprocess.run(
        [VENV_PY, SIGNAL_LOOP, "auto-generate"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if r2.returncode != 0:
        sys.stderr.write(f"signal_loop failed rc={r2.returncode}\n")
        if r2.stderr:
            sys.stderr.write(r2.stderr)
        elif r2.stdout:
            sys.stderr.write(r2.stdout[:1000])
        sys.exit(r2.returncode)
    sig = {}
    if r2.stdout:
        try:
            raw = r2.stdout.strip()
            brace = raw.find("{")
            if brace >= 0:
                sig = json.loads(raw[brace:])
            else:
                sig = json.loads(raw)
        except json.JSONDecodeError:
            sig = {"raw": r2.stdout[:1000]}

    explainability = {
        "constraints": _constraint_explainability(morning.get("constraints") or []),
    }
    model_risk_ledger = _build_model_risk_ledger(
        feature_snapshot=feature_snapshot,
        quant_bundle=quant_bundle,
        signal_auto_generate=sig,
        generated_at=morning.get("generated_at"),
        event_risk=morning.get("event_risk") or {},
    )

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
        "feature_snapshot": feature_snapshot,
        "feature_snapshot_path": "/config/quant_scripts/data/feature_snapshot.json",
        "signal_auto_generate": sig,
        "explainability": explainability,
        "model_risk_ledger": model_risk_ledger,
    }
    with open(PLAN_JSON, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    digest = _run_digest()
    plan["digest"] = digest
    plan["wechat_work_report_body"] = digest.get("wechat_work_report_body") or digest.get("digest_text", "")
    plan["push_wechat_required"] = bool(digest.get("push_wechat_required", True))
    plan["wechat_report_type"] = digest.get("wechat_report_type", "②工作报告-早计划")
    plan["needs_hermes"] = True
    plan["instruction"] = digest.get(
        "instruction",
        "必读 wechat_work_report_body；润色扩展后作为最终回复推微信（deliver=origin）。禁止跳过 digest。",
    )
    with open(PLAN_JSON, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    plan["plan_bundle_path"] = PLAN_JSON
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
