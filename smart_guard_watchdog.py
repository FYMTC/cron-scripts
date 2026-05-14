#!/config/quant_env/bin/python3
"""
smart_guard 进程监管 — watchdog cron 脚本
========================================
检查 smart_guard_v3.py 是否在运行，不在则自动重启。
H8: 交易时段内若进程在但心跳文件过期（疑似僵死），同样 kill+nohup 重启。
输出状态报告供 cron 上下文使用。
"""
import subprocess
import sys
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

GUARD_PY = "/config/quant_scripts/smart_guard_v3.py"
GUARD_LOG = "/config/quant_scripts/guard_daemon.log"
HEARTBEAT_FILE = "/config/quant_scripts/guard_heartbeat.txt"
PYTHON = "/config/quant_env/bin/python"
# 主循环约 30s/轮；超过该阈值视为无有效心跳
STALE_HEARTBEAT_SEC = 150


def _bj_now():
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def _in_weekday_market_watch_window():
    """北京时间工作日 09:00–16:00：应能持续收到 guard 心跳。"""
    t = _bj_now()
    if t.weekday() >= 5:
        return False
    h, m = t.hour, t.minute
    if h < 9:
        return False
    if h > 16:
        return False
    if h == 16 and m > 0:
        return False
    return True


def _heartbeat_age_sec():
    """返回最近一次心跳距现在的秒数；无文件视为极大。"""
    try:
        if not os.path.isfile(HEARTBEAT_FILE):
            return 999999.0
        return max(0.0, time.time() - os.path.getmtime(HEARTBEAT_FILE))
    except OSError:
        return 999999.0


def check_running():
    """检查 smart_guard 进程是否存在"""
    try:
        r = subprocess.run(
            ["pgrep", "-f", "smart_guard_v3.py"],
            capture_output=True, text=True, timeout=5
        )
        pids = [p for p in r.stdout.strip().split("\n") if p]
        return len(pids) > 0, pids
    except:
        return False, []

def restart_guard():
    """重启守护进程"""
    try:
        # Kill any existing instances first
        subprocess.run(["pkill", "-f", "smart_guard_v3.py"], 
                       capture_output=True, timeout=5)
        time.sleep(2)
        
        # Start with nohup
        with open(GUARD_LOG, "a") as log:
            log.write(f"\n=== Watchdog restart at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        
        subprocess.Popen(
            ["nohup", PYTHON, "-u", GUARD_PY],
            stdout=open(GUARD_LOG, "a"),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setpgrp,
            cwd="/config/quant_scripts"
        )
        time.sleep(3)
        
        running, pids = check_running()
        return running, pids
    except Exception as e:
        return False, str(e)[:100]

if __name__ == "__main__":
    running, pids = check_running()

    if running and _in_weekday_market_watch_window():
        age = _heartbeat_age_sec()
        if age > STALE_HEARTBEAT_SEC:
            print(
                f"[Watchdog] smart_guard ZOMBIE? process up but heartbeat stale "
                f"({age:.0f}s > {STALE_HEARTBEAT_SEC}s) — forcing restart..."
            )
            success, result = restart_guard()
            if success:
                print(f"[Watchdog] smart_guard RESTARTED (heartbeat) | PIDs: {','.join(result)}")
            else:
                print(f"[Watchdog] smart_guard RESTART FAILED: {result}")
            sys.exit(0 if success else 1)

    if running:
        print(f"[Watchdog] smart_guard OK | PIDs: {','.join(pids)}")
        sys.exit(0)

    print("[Watchdog] smart_guard DOWN — attempting restart...")
    success, result = restart_guard()
    if success:
        print(f"[Watchdog] smart_guard RESTARTED | PIDs: {','.join(result)}")
    else:
        print(f"[Watchdog] smart_guard RESTART FAILED: {result}")
    sys.exit(0 if success else 1)
