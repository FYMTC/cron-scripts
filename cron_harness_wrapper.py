#!/config/quant_env/bin/python3
"""
cron_harness_wrapper.py — 通用cron harness包装器
用法: 挂载到所有cron的script字段
  不需要额外preflight: cron_harness_wrapper.py
  需要额外preflight:  cron_harness_wrapper.py /path/to/other_script.py

输出顺序:
  1. HARNESS PREFLIGHT (系统状态+不变式+验证要求)
  2. (可选) 指定脚本的输出
"""

import subprocess, sys, os

HARNESS_SCRIPT = "/config/.hermes/scripts/hermes_harness_preflight.py"
PYTHON = "/config/quant_env/bin/python3"

def run_harness():
    r = subprocess.run([PYTHON, HARNESS_SCRIPT], capture_output=True, text=True, timeout=30)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.stderr:
        print(r.stderr, file=sys.stderr)
    return r.returncode

def run_additional(script_path):
    if not script_path or not os.path.exists(script_path):
        return 0
    r = subprocess.run([PYTHON, script_path], capture_output=True, text=True, timeout=120)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.stderr:
        print(r.stderr, file=sys.stderr)
    return r.returncode

if __name__ == "__main__":
    ec = 0
    ec |= run_harness()
    
    if len(sys.argv) > 1:
        ec |= run_additional(sys.argv[1])
    
    sys.exit(ec)
