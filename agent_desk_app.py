#!/config/quant_env/bin/python3
"""兼容入口 → agent_desk_poll_app（无 LLM）。"""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "agent_desk_poll_app.py"), run_name="__main__")
