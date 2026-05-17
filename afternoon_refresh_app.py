#!/config/quant_env/bin/python3
import os, subprocess, sys
r = subprocess.run(
    ["/config/quant_env/bin/python3", os.path.join(os.path.dirname(__file__), "data_refresh_app.py"), "afternoon"] + sys.argv[1:],
)
sys.exit(r.returncode)
