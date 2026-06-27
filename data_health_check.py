#!python3
"""
数据健康检查 — cron 脚本包装器
由 21:00 夜报 cron 以 script 参数调用，stdout 注入到 cron 上下文。
"""
import subprocess, sys
import sys; sys.path.insert(0, '/root/ai_trading_package/quant/quant_scripts')
from system_config import cfg

r = subprocess.run(
    [cfg.python, cfg.root + "/data_health.py"],
    capture_output=True, text=True, timeout=30
)
print(r.stdout)
if r.stderr:
    print(r.stderr, file=sys.stderr)
sys.exit(r.returncode)
