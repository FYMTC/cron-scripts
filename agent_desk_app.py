#!/usr/local/bin/python3
"""兼容入口 → agent_desk_poll_app（无 LLM）。"""
import runpy
from pathlib import Path
import sys; sys.path.insert(0, '/config/quant_scripts')
from system_config import cfg

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "agent_desk_poll_app.py"), run_name="__main__")
