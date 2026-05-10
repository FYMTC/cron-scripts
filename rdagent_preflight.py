#!/config/quant_env/bin/python3
"""周末因子挖掘 + HARNESS 前置"""
import subprocess, sys

HARNESS = "/config/.hermes/scripts/hermes_harness_preflight.py"
PYTHON = "/config/quant_env/bin/python"
RDAGENT_WRAPPER = "/config/quant_scripts/rdagent_weekend_preflight.py"

# Step 0: Harness preflight
r = subprocess.run([PYTHON, HARNESS], capture_output=True, text=True, timeout=30)
if r.stdout.strip():
    print(r.stdout.strip())

# Step 1: RD-Agent因子挖掘
r = subprocess.run([PYTHON, RDAGENT_WRAPPER], capture_output=True, text=True, timeout=600)
if r.stdout.strip():
    print(r.stdout.strip())
if r.stderr:
    print(r.stderr, file=sys.stderr)
sys.exit(r.returncode)
