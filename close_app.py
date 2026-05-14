#!/config/quant_env/bin/python3
"""15:05 收盘 — 先跑 signal 校验链，再 apps/close.py 产出 JSON，stdout 仅回显 close JSON。"""
import os
import subprocess
import sys

VENV_PY = "/config/quant_env/bin/python3"
VERIFY = "/config/.hermes/scripts/signal_verify_report.py"
APP = "/config/quant_scripts/apps/close.py"
OUT = "/config/quant_scripts/data/close_output.json"


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    r0 = subprocess.run([VENV_PY, VERIFY], capture_output=True, text=True, timeout=120)
    if r0.stdout:
        sys.stderr.write(r0.stdout)
    if r0.stderr:
        sys.stderr.write(r0.stderr)
    if r0.returncode != 0:
        sys.stderr.write(f"[close_app] signal_verify_report exit={r0.returncode}\n")

    r = subprocess.run([VENV_PY, APP, "--save", OUT], capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        print(f"❌ close.py exit={r.returncode}\nSTDERR:\n{r.stderr[:2000]}", file=sys.stderr)
        if r.stdout:
            print(r.stdout[:2000], file=sys.stderr)
        sys.exit(r.returncode)
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            print(f.read(), end="")
    else:
        print("❌ close.py ran but output JSON not found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
