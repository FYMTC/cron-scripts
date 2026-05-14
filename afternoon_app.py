#!/config/quant_env/bin/python3
"""14:00 下午速报 — apps/afternoon.py 薄封装，stdout 回显 JSON。"""
import os
import subprocess
import sys

APP = "/config/quant_scripts/apps/afternoon.py"
VENV_PY = "/config/quant_env/bin/python3"
OUT = "/config/quant_scripts/data/afternoon_output.json"


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    r = subprocess.run([VENV_PY, APP, "--save", OUT], capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        print(f"❌ afternoon.py exit={r.returncode}\nSTDERR:\n{r.stderr[:2000]}", file=sys.stderr)
        if r.stdout:
            print(r.stdout[:2000], file=sys.stderr)
        sys.exit(r.returncode)
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            print(f.read(), end="")
    else:
        print("❌ afternoon.py ran but output JSON not found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
