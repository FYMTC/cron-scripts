#!/config/quant_env/bin/python3
"""morning_app.py — apps/morning.py 薄封装"""
import subprocess, sys
r = subprocess.run(
    ["/config/quant_env/bin/python", "/config/quant_scripts/apps/morning.py",
     "--save", "/config/quant_scripts/data/morning_output.json"],
    capture_output=True, text=True, timeout=120)
sys.stdout.write(r.stdout)
if r.stderr:
    sys.stderr.write(r.stderr)
sys.exit(r.returncode)
