#!/config/quant_env/bin/python3
"""
紧急通道 */1 — 先 harness，再把 guard_emergency_signal.txt 打成 JSON 供 Agent 只读。
（不替代 prompt 内 signal_loop 闭环节点；stdout 为 JSON，harness/原文预览走 stderr）
"""
import json
import os
import subprocess
import sys
from datetime import datetime

VENV_PY = "/config/quant_env/bin/python3"
HARNESS = "/config/.hermes/scripts/hermes_harness_preflight.py"
SIG = "/config/quant_scripts/guard_emergency_signal.txt"
ALT = "/config/quant_scripts/guard_emergency.txt"


def main():
    r = subprocess.run([VENV_PY, HARNESS], capture_output=True, text=True, timeout=45)
    if r.stdout:
        sys.stderr.write(r.stdout)
    if r.stderr:
        sys.stderr.write(r.stderr)

    body = ""
    if os.path.exists(SIG):
        with open(SIG, encoding="utf-8", errors="replace") as f:
            body = f.read().strip()
    alt_body = ""
    if os.path.exists(ALT):
        with open(ALT, encoding="utf-8", errors="replace") as f:
            alt_body = f.read().strip()

    lines = [
        ln.strip()
        for ln in body.splitlines()
        if ln.strip() and ("AGENT_ALERT" in ln or "[AGENT_ALERT]" in ln)
    ]

    has_alert = len(lines) > 0
    print(f"emergency_signal: nonempty={len(body) > 0} agent_alerts={len(lines)}")
    # 不输出JSON——cron系统 .lower() 会崩在嵌套dict
    sys.exit(0)


if __name__ == "__main__":
    main()
