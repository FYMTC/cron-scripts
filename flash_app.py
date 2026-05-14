#!/usr/bin/env python3
"""
flash_app.py — 薄封装：调用 apps/flash.py --save，然后 stdout 回显 JSON。

cron 配置：
  script=/config/.hermes/scripts/flash_app.py
  prompt: 短 prompt，只读取 output JSON + 四步门禁，不嵌 bash。
  workdir: 不需单独设置（脚本内置绝对路径）

用法（cron 定期执行）:
  /config/.hermes/scripts/flash_app.py
"""

import subprocess, sys, os, json

APP = "/config/quant_scripts/apps/flash.py"
VENV_PY = "/config/quant_env/bin/python3"
OUT = "/config/quant_scripts/data/flash_output.json"

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    r = subprocess.run(
        [VENV_PY, APP, "--save", OUT],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0:
        print(f"❌ flash.py exit={r.returncode}\nSTDERR:\n{r.stderr[:1000]}")
        sys.exit(r.returncode)
    # 读回 JSON 写 stdout（保证 cron 日志有内容可追溯）
    if os.path.exists(OUT):
        with open(OUT) as f:
            json_str = f.read()
        print(json_str, end='')
    else:
        print("❌ flash.py ran but output JSON not found")
        sys.exit(1)

if __name__ == "__main__":
    main()
