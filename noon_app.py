#!python3
"""11:30 午间 — apps/noon.py 薄封装，stdout 回显 JSON。"""
import os
import subprocess
import sys
import sys; sys.path.insert(0, '/root/ai_trading_package/quant/quant_scripts')
from system_config import cfg

APP = cfg.path.apps_dir + "/noon.py"
VENV_PY = cfg.python  # 2026-06-27 修复：用 quant_env python（含 numpy/qlib），原裸 "python3" 缺依赖
OUT = cfg.path.noon_output


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
