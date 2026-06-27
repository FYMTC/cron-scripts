#!python3
import os, subprocess, sys
import sys; sys.path.insert(0, '/config/quant_scripts')
from system_config import cfg
r = subprocess.run(
    [cfg.python, os.path.join(os.path.dirname(__file__), "data_refresh_app.py"), "midday"] + sys.argv[1:],  # 2026-06-27: 用 quant_env python
)
sys.exit(r.returncode)
