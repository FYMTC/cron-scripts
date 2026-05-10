#!/config/quant_env/bin/python3
"""系统组件审计 + HARNESS 前置"""
import subprocess, sys

HARNESS = "/config/.hermes/scripts/hermes_harness_preflight.py"
AUDIT = "/config/quant_scripts/system_component_audit.py"
PYTHON = "/config/quant_env/bin/python"

r = subprocess.run([PYTHON, HARNESS], capture_output=True, text=True, timeout=30)
if r.stdout.strip():
    print(r.stdout.strip())
if r.stderr:
    print(r.stderr, file=sys.stderr)

r = subprocess.run([PYTHON, AUDIT, "--push"], capture_output=True, text=True, timeout=60)
print(r.stdout)
if r.stderr:
    print(r.stderr, file=sys.stderr)
sys.exit(r.returncode)
