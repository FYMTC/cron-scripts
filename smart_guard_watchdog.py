#!/config/quant_env/bin/python3
"""
smart_guard 进程监管 — watchdog cron 脚本
========================================
检查 smart_guard_v3.py 是否在运行，不在则自动重启。
输出状态报告供 cron 上下文使用。
"""
import subprocess, sys, os, time

GUARD_PY = "/config/quant_scripts/smart_guard_v3.py"
GUARD_LOG = "/config/quant_scripts/guard_daemon.log"
PYTHON = "/config/quant_env/bin/python"

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
    
    if running:
        print(f"[Watchdog] smart_guard OK | PIDs: {','.join(pids)}")
        sys.exit(0)
    else:
        print(f"[Watchdog] smart_guard DOWN — attempting restart...")
        success, result = restart_guard()
        if success:
            print(f"[Watchdog] smart_guard RESTARTED | PIDs: {','.join(result)}")
        else:
            print(f"[Watchdog] smart_guard RESTART FAILED: {result}")
        sys.exit(0 if success else 1)
