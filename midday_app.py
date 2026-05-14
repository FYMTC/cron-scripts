#!/usr/bin/env python3
"""
midday_app.py — 薄封装：调用 apps/midday.py --save，stdout 回显 JSON。

cron 配置：
  script=/config/.hermes/scripts/midday_app.py
  prompt: 短 prompt，只读取 output JSON + 四步门禁，不嵌 bash。

用法（cron 定期执行）:
  /config/.hermes/scripts/midday_app.py
"""

import subprocess, sys, os, json

APP = "/config/quant_scripts/apps/midday.py"
VENV_PY = "/config/quant_env/bin/python3"
OUT = "/config/quant_scripts/data/midday_output.json"

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    r = subprocess.run(
        [VENV_PY, APP, "--save", OUT],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0:
        print(f"❌ midday.py exit={r.returncode}\nSTDERR:\n{r.stderr[:1000]}")
        sys.exit(r.returncode)
    if os.path.exists(OUT):
        with open(OUT) as f:
            print(f.read(), end='')
    else:
        print("❌ midday.py ran but output JSON not found")
        sys.exit(1)

if __name__ == "__main__":
    main()
