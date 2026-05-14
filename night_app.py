#!/config/quant_env/bin/python3
"""21:00 夜报 — 先 night_preflight（选股/审计等），再 apps/night.py 聚合 JSON；stdout 仅回显 night JSON。"""
import os
import subprocess
import sys

VENV_PY = "/config/quant_env/bin/python3"
PREFLIGHT = "/config/.hermes/scripts/night_preflight.py"
APP = "/config/quant_scripts/apps/night.py"
OUT = "/config/quant_scripts/data/night_output.json"


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    r0 = subprocess.run([VENV_PY, PREFLIGHT], capture_output=True, text=True, timeout=900)
    if r0.stdout:
        sys.stderr.write(r0.stdout)
    if r0.stderr:
        sys.stderr.write(r0.stderr)
    if r0.returncode != 0:
        sys.stderr.write(f"[night_app] night_preflight exit={r0.returncode}\n")

    r = subprocess.run([VENV_PY, APP, "--save", OUT], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"❌ night.py exit={r.returncode}\nSTDERR:\n{r.stderr[:2000]}", file=sys.stderr)
        if r.stdout:
            print(r.stdout[:2000], file=sys.stderr)
        sys.exit(r.returncode)
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            print(f.read(), end="")
    else:
        print("❌ night.py ran but output JSON not found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
