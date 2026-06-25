#!python3
"""15:05 信号验证 + HARNESS 前置"""
import subprocess, sys
import sys; sys.path.insert(0, '/config/quant_scripts')
from system_config import cfg

HARNESS = cfg.system.hermes_root + "/scripts/hermes_harness_preflight.py"
EXEC = cfg.root + "/signal_executor.py"
PYTHON = cfg.python

# Step 0: Harness preflight (系统状态+不变式+验证要求)
r = subprocess.run([PYTHON, HARNESS], capture_output=True, text=True, timeout=30)
if r.stdout.strip():
    print(r.stdout.strip())

# Steps 1-3: 信号验证
def run(cmd):
    r = subprocess.run([PYTHON, EXEC] + cmd, capture_output=True, text=True, timeout=30,
                       cwd=cfg.root)
    return r.stdout.strip(), r.stderr.strip()

out, err = run(["verify", "--min-days", "1"])
print(f"[SignalEngine] {out}")
out, err = run(["report"])
print(f"[SignalEngine] {out}")
out, err = run(["expire"])
print(f"[SignalEngine] {out}")
