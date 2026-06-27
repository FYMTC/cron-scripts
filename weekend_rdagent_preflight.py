#!python3
"""周六薄封装：始终带 --save-weekend-data，供多个 job 共用同一 script 字段。"""
import subprocess
import sys
import sys; sys.path.insert(0, '/config/quant_scripts')
from system_config import cfg

PY = cfg.python  # 2026-06-27 修复：用 quant_env python（含 numpy/qlib），原裸 "python3" 缺依赖
SCRIPT = cfg.system.hermes_root + "/scripts/rdagent_preflight.py"

if __name__ == "__main__":
    r = subprocess.run([PY, SCRIPT, "--save-weekend-data"] + sys.argv[1:])
    sys.exit(r.returncode)
