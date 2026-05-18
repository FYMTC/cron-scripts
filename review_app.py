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
OUT = "/config/quant_scripts/data/night_output.json"
REVIEW_JSON = "/config/quant_scripts/data/review_bundle.json"


def _run_digest() -> dict:
    r = subprocess.run([VENV_PY, DIGEST, "night"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout or "digest failed")[:300]}
    raw = (r.stdout or "").strip()
    brace = raw.find("{")
    if brace >= 0:
        return json.loads(raw[brace:])
    return json.loads(raw)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bundle = {"generated_at": datetime.now().isoformat(), "phase": "review", "steps": {}}

    r_sc = subprocess.run([VENV_PY, SELF_CHECK, "--json"], capture_output=True, text=True, timeout=180)
    self_check = {"exit_code": r_sc.returncode, "ok": r_sc.returncode == 0}
    if r_sc.stdout:
        try:
            self_check.update(json.loads(r_sc.stdout))
        except json.JSONDecodeError:
            self_check["raw"] = r_sc.stdout[:800]
    bundle["steps"]["v5_self_check"] = self_check
    bundle["v5_self_check_ok"] = self_check.get("ok", r_sc.returncode == 0)

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

    r3 = subprocess.run([VENV_PY, CVRF], capture_output=True, text=True, timeout=180)
    bundle["steps"]["cvrf_reflection"] = {"exit_code": r3.returncode}
    if r3.stdout:
        bundle["cvrf_stdout_preview"] = r3.stdout[:1200]

    night = {}
    if os.path.isfile(OUT):
        with open(OUT, encoding="utf-8") as f:
            night = json.load(f)

    bundle["ok"] = True
    bundle["night_output_path"] = OUT
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

    with open(REVIEW_JSON, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)
    bundle["review_bundle_path"] = REVIEW_JSON
    print(json.dumps(bundle, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
