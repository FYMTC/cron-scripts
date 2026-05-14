#!/config/quant_env/bin/python3
"""morning_app.py — apps/morning.py 薄封装（供 Hermes cron script 字段调用）"""

import subprocess
import sys

OUT = "/config/quant_scripts/data/morning_output.json"
PY = "/config/quant_env/bin/python"
APP = "/config/quant_scripts/apps/morning.py"

r = subprocess.run(
    [PY, APP, "--save", OUT],
    capture_output=True,
    text=True,
    timeout=120,
)
if r.stderr:
    sys.stderr.write(r.stderr)
if r.returncode != 0:
    sys.stderr.write(r.stdout or "")
    sys.exit(r.returncode)

# morning.py --save 把 JSON 写入文件，父进程 stdout 为空；此处读回便于 cron 日志与排错
try:
    with open(OUT, encoding="utf-8") as f:
        body = f.read()
    if body.strip():
        sys.stdout.write(body)
    elif r.stdout:
        sys.stdout.write(r.stdout)
except OSError as e:
    sys.stderr.write(f"[morning_app] read {OUT}: {e}\n")
    sys.exit(1)
sys.exit(0)
