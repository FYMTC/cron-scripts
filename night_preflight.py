#!/config/quant_env/bin/python3
"""21:00 夜报前置 — 信号 + 风险 + 数据 + 审计 + CVRF + Q-phase全量量化"""
import json
import re
import subprocess
import sys
from datetime import datetime

PY = "/config/quant_env/bin/python3"
SCRIPTS = [
    [PY, "/config/.hermes/scripts/hermes_harness_preflight.py"],
    # 选股引擎: 全市场扫描→落盘(供明日08:30盘前简报读取)
    [PY, "/config/quant_scripts/stock_screener.py", "--top", "15", "--save", "/config/quant_scripts/data/screener_top15.json"],
    [PY, "/config/quant_scripts/signal_executor.py", "verify", "--min-days", "1"],
    [PY, "/config/quant_scripts/signal_executor.py", "report"],
    [PY, "/config/quant_scripts/signal_executor.py", "expire"],
    [PY, "/config/quant_scripts/signal_lifecycle.py", "audit"],
    [PY, "/config/quant_scripts/risk_monitor.py", "--json"],  # GARCH+GBM+Copula已内置
    [PY, "/config/quant_scripts/market_regime.py", "--json"],  # HMM市场状态
    [PY, "/config/quant_scripts/stat_arb.py", "--json"],  # Q3.1: 协整统计套利
    [PY, "/config/quant_scripts/dl_predictor.py", "--code", "000063", "--horizon", "5", "--json"],  # Q4.1: LSTM
    [PY, "/config/quant_scripts/factor_pca.py", "--json"],  # PCA因子降维
    [PY, "/config/quant_scripts/data_health.py"],
    [PY, "/config/quant_scripts/system_component_audit.py"],
    [PY, "/config/quant_scripts/cvrf_reflection.py"],
    [PY, "/config/quant_scripts/manifest_touch.py", "--cron-id", "dd8c45af9154"],
]

NIGHT_QUANT_JSON = "/config/quant_scripts/data/night_quant.json"


def _json_module_key(cmd: list) -> str | None:
    if "--json" not in cmd:
        return None
    path = cmd[1]
    if "risk_monitor" in path:
        return "risk_monitor"
    if "market_regime" in path:
        return "market_regime"
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


def main() -> None:
    quant_modules: dict[str, object] = {}
    for cmd in SCRIPTS:
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


if __name__ == "__main__":
    main()
