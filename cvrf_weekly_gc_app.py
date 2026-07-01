#!python3
"""周六04:00 薄封装：调 cvrf_reflection.py --mode weekly-gc 跑周度经验 GC。"""
import subprocess
import sys
import sys; sys.path.insert(0, '/root/ai_trading_package/quant/quant_scripts')
from system_config import cfg

PY = cfg.python  # 2026-06-30：用 quant_env python（含 baostock），原裸 "python3" 缺依赖
SCRIPT = '/root/ai_trading_package/quant/quant_scripts/cvrf_reflection.py'

if __name__ == "__main__":
    r = subprocess.run([PY, SCRIPT, "--mode", "weekly-gc"] + sys.argv[1:])
    sys.exit(r.returncode)
