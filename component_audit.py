#!python3
"""系统组件审计 + HARNESS 前置"""
import subprocess, sys
import sys; sys.path.insert(0, '/config/quant_scripts')
from system_config import cfg

HARNESS = cfg.system.hermes_root + "/scripts/hermes_harness_preflight.py"
AUDIT = cfg.root + "/system_component_audit.py"
PYTHON = cfg.python  # 2026-06-27 修复：用 quant_env python（含 numpy/qlib），原裸 "python3" 缺依赖

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
