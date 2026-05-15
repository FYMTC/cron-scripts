#!/config/quant_env/bin/python3
"""11:30 午间 — apps/noon.py 薄封装，stdout 回显 JSON。"""
import os
import subprocess
import sys

APP = "/config/quant_scripts/apps/noon.py"
VENV_PY = "/config/quant_env/bin/python3"
OUT = "/config/quant_scripts/data/noon_output.json"


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    r = subprocess.run([VENV_PY, APP, "--save", OUT], capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        print(f"❌ noon.py exit={r.returncode}\nSTDERR:\n{r.stderr[:2000]}", file=sys.stderr)
        if r.stdout:
            print(r.stdout[:2000], file=sys.stderr)
        sys.exit(r.returncode)
    if os.path.exists(OUT):
        import json as _json
        with open(OUT, encoding="utf-8") as f:
            _d = _json.load(f)
        _h = len(_d.get("holdings", []))
        _a = len(_d.get("alerts", []))
        _r = _d.get("recommendation", "?")
        print(f"noon_output ready: {_h}持仓 {_a}告警 recommendation={_r}")
        print(f"JSON saved to {OUT}")
    else:
        print("❌ noon.py ran but output JSON not found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
