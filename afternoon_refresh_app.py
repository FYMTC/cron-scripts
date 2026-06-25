#!python3
import os, subprocess, sys
import sys; sys.path.insert(0, '/config/quant_scripts')
from system_config import cfg
r = subprocess.run(
    ["python3", os.path.join(os.path.dirname(__file__), "data_refresh_app.py"), "afternoon"] + sys.argv[1:],
)
sys.exit(r.returncode)
