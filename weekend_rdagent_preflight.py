#!/config/quant_env/bin/python3
"""周六薄封装：始终带 --save-weekend-data，供多个 job 共用同一 script 字段。"""
import subprocess
import sys

PY = "/config/quant_env/bin/python3"
SCRIPT = "/config/.hermes/scripts/rdagent_preflight.py"

if __name__ == "__main__":
    r = subprocess.run([PY, SCRIPT, "--save-weekend-data"] + sys.argv[1:])
    sys.exit(r.returncode)
