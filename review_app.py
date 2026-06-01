#!/config/quant_env/bin/python3
"""
收盘 Review 薄封装（P4）：night_preflight + night + signal_audit + cvrf 摘要 JSON。
"""
import json
import os
import subprocess
import sys
from datetime import datetime

VENV_PY = "/config/quant_env/bin/python3"
PREFLIGHT = "/config/.hermes/scripts/night_preflight.py"
SELF_CHECK = "/config/quant_scripts/v5_self_check.py"
NIGHT = "/config/quant_scripts/apps/night.py"
AUDIT = "/config/quant_scripts/signal_audit.py"
CVRF = "/config/quant_scripts/cvrf_reflection.py"
DIGEST = os.path.join(os.path.dirname(__file__), "digest_app.py")
RUNTIME_DATA_DIR = os.environ.get("QUANT_RUNTIME_DATA_DIR") or "/config/quant_scripts/data"
OUT = os.path.join(RUNTIME_DATA_DIR, "night_output.json")
REVIEW_JSON = os.path.join(RUNTIME_DATA_DIR, "review_bundle.json")
FEATURE_SNAPSHOT_JSON = os.path.join(RUNTIME_DATA_DIR, "feature_snapshot.json")
PLAN_JSON = os.path.join(RUNTIME_DATA_DIR, "plan_bundle.json")
WIKI_REPORTS_DIR = os.environ.get("QUANT_WIKI_REPORTS_DIR") or "/config/quant-wiki/reports"
TEST_MODE = bool(os.environ.get("QUANT_RUNTIME_SCENARIO") or os.environ.get("QUANT_TEST_MODE"))


sys.path.insert(0, "/config/quant_scripts")

from trade_notify import enqueue_wechat


def _save_report_copy(body: str, generated_at: str, tag: str) -> None:
    if not body or not generated_at:
        return
    try:
        os.makedirs(WIKI_REPORTS_DIR, exist_ok=True)
        date_str = generated_at[:10]
        path = os.path.join(WIKI_REPORTS_DIR, f"{date_str}-{tag}.md")
        label = {"morning-plan": "早报", "night-review": "夜报"}.get(tag, tag)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {label} — {generated_at[:19]}\n\n")
            f.write(f"> 来源: {tag} bundle · {len(body)} 字符\n\n")
            f.write(body)
    except OSError:
        pass


def _run_digest() -> dict:
    r = subprocess.run([VENV_PY, DIGEST, "night"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout or "digest failed")[:300]}
    raw = (r.stdout or "").strip()
    brace = raw.find("{")
    if brace >= 0:
        return json.loads(raw[brace:])
    return json.loads(raw)


def _extract_json_object(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}
    decoder = json.JSONDecoder()
    found = []
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
            if isinstance(obj, dict):
                found.append(obj)
        except json.JSONDecodeError:
            continue
    for obj in reversed(found):
        if "checks" in obj or "phase" in obj:
            return obj
    return found[-1] if found else {}


def _counterfactual_examples(plan_bundle: dict) -> dict:
    explainability = (plan_bundle or {}).get("explainability") or {}
    constraints = explainability.get("constraints") or {}
    return {
        "plan_constraints": constraints,
        "has_counterfactual": bool(constraints),
    }


def _build_model_risk_ledger(plan_bundle: dict, feature_snapshot: dict) -> dict:
    feature_runtime = (feature_snapshot or {}).get("runtime_flags") or {}
    portfolio = (feature_snapshot or {}).get("portfolio") or {}
    event_risk = portfolio.get("event_risk") or {}
    quant_bundle = (plan_bundle or {}).get("quant_bundle") or {}
    signal_auto_generate = (plan_bundle or {}).get("signal_auto_generate") or {}
    event_risk_plan = (plan_bundle or {}).get("event_risk") or {}
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
            "as_of": event_risk_plan.get("assessed_at") or (feature_snapshot or {}).get("generated_at"),
            "version": event_risk_plan.get("date") or (feature_snapshot or {}).get("as_of_date"),
            "status": "ok" if (event_risk_plan or {}).get("event_level") else "fallback",
            "degraded": not bool((event_risk_plan or {}).get("event_level")),
            "fallback_reason": None if (event_risk_plan or {}).get("event_level") else "event_risk_data_missing",
        },
        {
            "name": "signal_auto_generate",
            "type": "signal_engine",
            "source_modules": ["signal_loop"],
            "as_of": (plan_bundle or {}).get("generated_at"),
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


def _enqueue_report(body: str, report_type: str, bundle_path: str, generated_at: str) -> dict:
    if not body.strip():
        return {"ok": False, "skipped": True, "reason": "empty_report_body"}
    return enqueue_wechat(
        body,
        kind="work_report",
        meta={
            "report_type": report_type,
            "phase": "review",
            "bundle_path": bundle_path,
            "generated_at": generated_at,
        },
    )


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bundle = {"generated_at": datetime.now().isoformat(), "phase": "review", "steps": {}}

    if TEST_MODE:
        self_check = {"exit_code": 0, "ok": True, "skipped": "test_mode"}
    else:
        r_sc = subprocess.run([VENV_PY, SELF_CHECK, "--json"], capture_output=True, text=True, timeout=180)
        self_check = {"exit_code": r_sc.returncode, "ok": r_sc.returncode == 0}
        if r_sc.stdout:
            parsed = _extract_json_object(r_sc.stdout)
            if parsed:
                self_check.update(parsed)
            else:
                self_check["raw"] = r_sc.stdout[:800]
    bundle["steps"]["v5_self_check"] = self_check
    bundle["v5_self_check_ok"] = bool(self_check.get("ok", False))

    r0 = subprocess.run([VENV_PY, PREFLIGHT], capture_output=True, text=True, timeout=900)
    bundle["steps"]["night_preflight"] = {"exit_code": r0.returncode}
    if r0.stderr:
        sys.stderr.write(r0.stderr[-2000:])

    r1 = subprocess.run([VENV_PY, NIGHT, "--save", OUT], capture_output=True, text=True, timeout=120)
    bundle["steps"]["night"] = {"exit_code": r1.returncode, "path": OUT}
    if r1.returncode != 0:
        bundle["ok"] = False
        bundle["needs_hermes"] = False
        bundle["error"] = (r1.stderr or "")[:500]
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        sys.exit(r1.returncode)

    r2 = subprocess.run([VENV_PY, AUDIT, "daily"], capture_output=True, text=True, timeout=120)
    audit = {}
    if r2.stdout:
        try:
            audit = json.loads(r2.stdout)
        except json.JSONDecodeError:
            audit = {"raw": r2.stdout[:1500]}
    bundle["steps"]["signal_audit"] = {"exit_code": r2.returncode}
    bundle["signal_audit"] = audit

    r3 = None
    if TEST_MODE:
        bundle["steps"]["cvrf_reflection"] = {"exit_code": 0, "skipped": "test_mode"}
    else:
        r3 = subprocess.run([VENV_PY, CVRF], capture_output=True, text=True, timeout=180)
        bundle["steps"]["cvrf_reflection"] = {"exit_code": r3.returncode}
        if r3.stdout:
            bundle["cvrf_stdout_preview"] = r3.stdout[:1200]

    night = {}
    if os.path.isfile(OUT):
        with open(OUT, encoding="utf-8") as f:
            night = json.load(f)

    feature_snapshot = {}
    if os.path.isfile(FEATURE_SNAPSHOT_JSON):
        with open(FEATURE_SNAPSHOT_JSON, encoding="utf-8") as f:
            feature_snapshot = json.load(f)
    plan_bundle = {}
    if os.path.isfile(PLAN_JSON):
        with open(PLAN_JSON, encoding="utf-8") as f:
            plan_bundle = json.load(f)

    bundle["feature_snapshot"] = {
        "generated_at": feature_snapshot.get("generated_at"),
        "per_stock_count": len(feature_snapshot.get("per_stock") or {}),
        "missing_codes": (feature_snapshot.get("runtime_flags") or {}).get("missing_codes") or [],
        "feature_fresh": (feature_snapshot.get("runtime_flags") or {}).get("feature_fresh"),
    }
    bundle["account_runtime"] = {
        "ok": self_check.get("checks", {}).get("primary_account_runtime", {}).get("ok"),
        "runtime_mode": self_check.get("checks", {}).get("primary_account_runtime", {}).get("runtime_mode"),
        "desk_primary_account": self_check.get("checks", {}).get("primary_account_runtime", {}).get("desk_primary_account"),
        "primary_account": self_check.get("checks", {}).get("primary_account_runtime", {}).get("primary_account") or {},
        "special_mode": bool(self_check.get("checks", {}).get("primary_account_runtime", {}).get("runtime_mode") == "multi_account_mode"),
    }
    signal_auto_generate = plan_bundle.get("signal_auto_generate") or {}
    bundle["runtime_research_consumption"] = {
        "plan_has_feature_snapshot": "feature_snapshot" in plan_bundle,
        "signal_auto_generate_feature_snapshot_used": signal_auto_generate.get("feature_snapshot_used"),
    }
    bundle["explainability"] = _counterfactual_examples(plan_bundle)
    bundle["model_risk_ledger"] = _build_model_risk_ledger(plan_bundle, feature_snapshot)

    bundle["ok"] = True
    bundle["night_output_path"] = OUT
    bundle["strategy_validation"] = night.get("strategy_validation")
    bundle["strategy_review"] = night.get("strategy_review")
    bundle["night_summary"] = {
        "recommendation": night.get("recommendation"),
        "holdings_count": len(night.get("holdings") or []),
        "has_preflight_modules": bool((night.get("quant") or {}).get("preflight_modules")),
    }
    digest = _run_digest()
    bundle["digest"] = digest
    bundle["wechat_work_report_body"] = digest.get("wechat_work_report_body") or digest.get("digest_text", "")
    bundle["push_wechat_required"] = bool(digest.get("push_wechat_required", True))
    bundle["wechat_report_type"] = digest.get("wechat_report_type", "②工作报告-晚复盘")
    bundle["needs_hermes"] = True
    instr = digest.get(
        "instruction",
        "以 wechat_work_report_body 为底稿写详细晚复盘；deliver=origin 自动推微信。",
    )
    if not bundle.get("v5_self_check_ok", True):
        instr += (
            " v5_self_check 失败：最终回复末尾另加③系统状态段，列出 failure_names 或 paths.missing。"
        )
    bundle["instruction"] = instr
    bundle["wechat_enqueue"] = _enqueue_report(
        bundle.get("wechat_work_report_body") or "",
        bundle.get("wechat_report_type") or "②工作报告-晚复盘",
        REVIEW_JSON,
        str(bundle.get("generated_at") or ""),
    )
    _save_report_copy(
        bundle.get("wechat_work_report_body") or "",
        str(bundle.get("generated_at") or ""),
        "night-review",
    )

    with open(REVIEW_JSON, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)
    bundle["review_bundle_path"] = REVIEW_JSON
    print(json.dumps(bundle, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
