#!/config/quant_env/bin/python3
"""21:00 夜报前置 — 信号 + 风险 + 数据 + 审计 + CVRF + Q-phase全量量化"""
import subprocess, sys

PY = "/config/quant_env/bin/python"
SCRIPTS = [
    [PY, "/config/.hermes/scripts/hermes_harness_preflight.py"],
    [PY, "/config/quant_scripts/signal_executor.py", "verify", "--min-days", "1"],
    [PY, "/config/quant_scripts/signal_executor.py", "report"],
    [PY, "/config/quant_scripts/signal_executor.py", "expire"],
    [PY, "/config/quant_scripts/signal_lifecycle.py", "audit"],
    [PY, "/config/quant_scripts/risk_monitor.py", "--json"],       # GARCH+GBM+Copula已内置
    [PY, "/config/quant_scripts/market_regime.py", "--json"],      # HMM市场状态
    [PY, "/config/quant_scripts/stat_arb.py", "--json"],           # Q3.1: 协整统计套利
    [PY, "/config/quant_scripts/dl_predictor.py", "--code", "000063", "--horizon", "5", "--json"],  # Q4.1: LSTM
    [PY, "/config/quant_scripts/factor_pca.py", "--json"],         # PCA因子降维
    [PY, "/config/quant_scripts/data_health.py"],
    [PY, "/config/quant_scripts/system_component_audit.py"],
    [PY, "/config/quant_scripts/cvrf_reflection.py"],
    [PY, "/config/quant_scripts/manifest_touch.py", "--cron-id", "dd8c45af9154"],
]

for cmd in SCRIPTS:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        out = r.stdout.strip()
        if out:
            print(out)
        if r.stderr:
            print(r.stderr, file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] {' '.join(cmd[:2])}: {e}", file=sys.stderr)
