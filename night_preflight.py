#!/config/quant_env/bin/python3
"""21:00 夜报前置 — 信号验证 + 风险监控 + 数据健康 + 组件审计 + CVRF"""
import subprocess, sys

PY = "/config/quant_env/bin/python"
SCRIPTS = [
    [PY, "/config/.hermes/scripts/hermes_harness_preflight.py"],
    [PY, "/config/quant_scripts/signal_executor.py", "verify", "--min-days", "1"],
    [PY, "/config/quant_scripts/signal_executor.py", "report"],
    [PY, "/config/quant_scripts/signal_executor.py", "expire"],
    [PY, "/config/quant_scripts/risk_monitor.py", "--json"],
    [PY, "/config/quant_scripts/data_health.py"],
    [PY, "/config/quant_scripts/system_component_audit.py"],
    [PY, "/config/quant_scripts/cvrf_reflection.py"],
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
