#!/config/quant_env/bin/python3
"""21:00 夜报前置 — 信号验证 + 风险监控 + 数据健康 + 组件审计 + CVRF + Q1量化方法"""
import subprocess, sys

PY = "/config/quant_env/bin/python"
SCRIPTS = [
    [PY, "/config/.hermes/scripts/hermes_harness_preflight.py"],
    [PY, "/config/quant_scripts/signal_executor.py", "verify", "--min-days", "1"],
    [PY, "/config/quant_scripts/signal_executor.py", "report"],
    [PY, "/config/quant_scripts/signal_executor.py", "expire"],
    # DS-1: 信号生命周期审计
    [PY, "/config/quant_scripts/signal_lifecycle.py", "audit"],
    [PY, "/config/quant_scripts/risk_monitor.py", "--json"],
    # Q1.2: HMM 市场状态识别（注入cron上下文）
    [PY, "/config/quant_scripts/market_regime.py", "--json"],
    # Q1.3: PCA 因子降维（Qlib数据可用时运行）
    [PY, "/config/quant_scripts/factor_pca.py", "--json"],
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
