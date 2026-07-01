#!python3
"""周六03:00 薄封装：调 rotation_scanner.py 扫行业轮动 + 内部串联 backtest_rotation 门槛。"""
import subprocess
import sys
import sys; sys.path.insert(0, '/root/ai_trading_package/quant/quant_scripts')
from system_config import cfg

PY = cfg.python  # 2026-06-30：用 quant_env python（含 baostock），原裸 "python3" 缺依赖
SCRIPT = '/root/ai_trading_package/quant/quant_scripts/rotation_scanner.py'

if __name__ == "__main__":
    r = subprocess.run([PY, SCRIPT] + sys.argv[1:])
    sys.exit(r.returncode)
