#!/usr/local/bin/python3
"""
启动恢复引导 — gateway 重启后自动 kickstart 交易系统。
每分钟运行，但每天只执行一次（用日期戳去重）。

当 gateway 在任意时间启动：
- 交易日 + 交易时段(08:40-16:00) → 启动 agent_desk + smart_guard
- 非交易时段 → 静默跳过（cron 本身会在下次窗口触发）
"""

import json
import os
import subprocess
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

BOOTSTRAP_STATE = "/config/quant_scripts/data/bootstrap_state.json"
SCRIPTS_DIR = "/root/.hermes/scripts"
PYTHON = "/usr/local/bin/python3"
CST = ZoneInfo("Asia/Shanghai")


def _today_key() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d")


def _already_bootstrapped() -> bool:
    try:
        if os.path.exists(BOOTSTRAP_STATE):
            with open(BOOTSTRAP_STATE) as f:
                state = json.load(f)
            return state.get("date") == _today_key() and state.get("done")
    except Exception:
        pass
    return False


def _mark_bootstrapped(steps: list) -> None:
    os.makedirs(os.path.dirname(BOOTSTRAP_STATE), exist_ok=True)
    with open(BOOTSTRAP_STATE, "w") as f:
        json.dump({
            "date": _today_key(),
            "done": True,
            "bootstrapped_at": datetime.now(CST).isoformat(),
            "steps": steps,
        }, f, indent=2)


def _in_trading_window() -> bool:
    """北京时间工作日 08:40–16:00"""
    t = datetime.now(CST)
    if t.weekday() >= 5:
        return False
    h, m = t.hour, t.minute
    if h < 8:
        return False
    if h == 8 and m < 40:
        return False
    if h > 16:
        return False
    return True


def _run_script(script_name: str) -> bool:
    path = os.path.join(SCRIPTS_DIR, script_name)
    try:
        r = subprocess.run(
            [PYTHON, path],
            capture_output=True, text=True, timeout=60,
            cwd="/config/quant_scripts",
        )
        ok = r.returncode == 0
        output = (r.stdout or "")[-200:]
        return ok, output
    except Exception as e:
        return False, str(e)[:200]


def main():
    if _already_bootstrapped():
        # 静默：今天已引导过
        return

    if not _in_trading_window():
        # 非交易时段：不引导，等 cron 到点自动触发
        return

    steps = []

    # 1. 启动 smart_guard 守护进程
    ok, out = _run_script("smart_guard_watchdog.py")
    steps.append({"step": "smart_guard", "ok": ok, "output": out[:200]})

    # 2. 启动 agent_desk 轮询
    ok, out = _run_script("agent_desk_poll_app.py")
    steps.append({"step": "agent_desk", "ok": ok, "output": out[:200]})

    _mark_bootstrapped(steps)

    # 输出摘要供 cron 日志
    statuses = [f"{s['step']}:{'OK' if s['ok'] else 'FAIL'}" for s in steps]
    print(f"[bootstrap] {_today_key()} {', '.join(statuses)}")


if __name__ == "__main__":
    main()
