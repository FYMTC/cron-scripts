#!/config/quant_env/bin/python3
"""21:00 夜报前置 — 信号验证 + 风险监控 + 数据健康 + 组件审计 + CVRF"""
import subprocess, sys

PY = "/config/quant_env/bin/python"
SCRIPTS = [
    [PY, "/config/.hermes/scripts/hermes_harness_preflight.py"],
    [PY, "/config/quant_scripts/signal_executor.py", "verify", "--min-days", "1"],
    [PY, "/config/quant_scripts/signal_executor.py", "report"],
    [PY, "/config/quant_scripts/signal_executor.py", "expire"],
    # DS-1: 信号生命周期审计（过期检测+冲突检测）
    [PY, "/config/quant_scripts/signal_lifecycle.py", "audit"],
    [PY, "/config/quant_scripts/risk_monitor.py", "--json"],
    [PY, "/config/quant_scripts/data_health.py"],
    [PY, "/config/quant_scripts/system_component_audit.py"],
    [PY, "/config/quant_scripts/cvrf_reflection.py"],
    # P2-6: manifest 自动回写（更新夜报组件时间戳）
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
