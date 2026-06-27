#!python3
"""21:00 夜报前置 — 信号 + 风险 + 数据 + 审计 + CVRF + Q-phase全量量化"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
import sys; sys.path.insert(0, '/config/quant_scripts')
from system_config import cfg

PY = cfg.python  # 2026-06-27 修复：用 quant_env python（含 numpy/qlib），原裸 "python3" 缺依赖
RUNTIME_DATA_DIR = cfg.data_dir
SCREENER_JSON = os.path.join(RUNTIME_DATA_DIR, "screener_top15.json")
NIGHT_QUANT_JSON = os.path.join(RUNTIME_DATA_DIR, "night_quant.json")
TEST_MODE = bool(os.environ.get("QUANT_RUNTIME_SCENARIO") or os.environ.get("QUANT_TEST_MODE"))
BASE_SCRIPTS = [
    [PY, cfg.system.hermes_root + "/scripts/hermes_harness_preflight.py"],
    [PY, cfg.root + "/core/engines/event_calendar.py", "--json", "--update-cron-state"],
    [PY, cfg.root + "/signal_executor.py", "verify", "--min-days", "1"],
    [PY, cfg.root + "/signal_executor.py", "report"],
    [PY, cfg.root + "/signal_executor.py", "expire"],
    [PY, cfg.root + "/signal_lifecycle.py", "audit"],
    [PY, cfg.root + "/risk_monitor.py", "--json"],
    [PY, cfg.root + "/data_health.py"],
]
FULL_ONLY_SCRIPTS = [
    [PY, cfg.root + "/stock_screener.py", "--top", "15", "--save", SCREENER_JSON],
    [PY, cfg.root + "/market_regime.py", "--json"],
    [PY, cfg.root + "/stat_arb.py", "--json"],
    [PY, cfg.root + "/dl_predictor.py", "--code", "000063", "--horizon", "5", "--json"],
    [PY, cfg.root + "/factor_pca.py", "--json"],
    [PY, cfg.root + "/system_component_audit.py"],
    [PY, cfg.root + "/cvrf_reflection.py"],
    [PY, cfg.root + "/manifest_touch.py", "--cron-id", "dd8c45af9154"],
]


def _scripts() -> list[list[str]]:
    scripts = list(BASE_SCRIPTS)
    if TEST_MODE:
        if not os.path.exists(SCREENER_JSON):
            scripts.append([PY, cfg.root + "/stock_screener.py", "--top", "15", "--save", SCREENER_JSON])
        return scripts
    scripts.extend(FULL_ONLY_SCRIPTS)
    return scripts


def _json_module_key(cmd: list):
    if "--json" not in cmd:
        return None
    path = cmd[1]
    if "risk_monitor" in path:
        return "risk_monitor"
    if "market_regime" in path:
        return "market_regime"
    if "event_calendar" in path:
        return "event_calendar"
    if "stat_arb" in path:
        return "stat_arb"
    if "dl_predictor" in path:
        return "dl_predictor"
    if "factor_pca" in path:
        return "factor_pca"
    return None


def _extract_json_from_stdout(text: str):
    """stdout 可能含 Baostock login 噪声；取最后一个完整 JSON 对象。"""
    if not text or not text.strip():
        return None
    s = text.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    for m in re.finditer(r"\{", s):
        start = m.start()
        chunk = s[start:]
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            continue
    return None


def _write_minimal_night_quant() -> None:
    payload = {
        "generated_at": datetime.now().isoformat(),
        "modules": {},
        "test_mode": True,
        "source": "night_preflight:minimal",
    }
    with open(NIGHT_QUANT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    os.makedirs(RUNTIME_DATA_DIR, exist_ok=True)
    quant_modules: dict[str, object] = {}
    for cmd in _scripts():
        key = _json_module_key(cmd)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            out = (r.stdout or "").strip()
            if out:
                print(out)
            if r.stderr:
                print(r.stderr, file=sys.stderr)
            if key and out:
                parsed = _extract_json_from_stdout(out)
                if parsed is not None:
                    quant_modules[key] = parsed
        except Exception as e:
            print(f"[ERROR] {' '.join(cmd[:2])}: {e}", file=sys.stderr)

    if quant_modules:
        payload = {
            "generated_at": datetime.now().isoformat(),
            "modules": quant_modules,
        }
        try:
            with open(NIGHT_QUANT_JSON, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"[night_preflight] wrote {NIGHT_QUANT_JSON}", file=sys.stderr)
        except OSError as e:
            print(f"[night_preflight] cannot write night_quant: {e}", file=sys.stderr)
    elif TEST_MODE and not os.path.exists(NIGHT_QUANT_JSON):
        try:
            _write_minimal_night_quant()
            print(f"[night_preflight] wrote minimal {NIGHT_QUANT_JSON}", file=sys.stderr)
        except OSError as e:
            print(f"[night_preflight] cannot write minimal night_quant: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
