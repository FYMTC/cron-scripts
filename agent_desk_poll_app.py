#!/config/quant_env/bin/python3
"""
Agent Desk 轮询（无 LLM）：*/5 仅跑 agent_desk.py。
needs_hermes=false → 零 token；true → 写 pending 并 `hermes cron run` LLM job。
"""
import json
import os
import subprocess
import sys
from datetime import datetime

VENV_PY = "/config/quant_env/bin/python3"
SCRIPTS = "/config/quant_scripts"
sys.path.insert(0, SCRIPTS)

import agent_desk_config as adc  # noqa: E402

DESK = os.path.join(SCRIPTS, "agent_desk.py")


def _run_desk() -> dict:
    r = subprocess.run(
        [VENV_PY, DESK, "--json", "--max", "5"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if r.stderr:
        sys.stderr.write(r.stderr)
    if r.returncode != 0:
        return {"needs_hermes": False, "error": (r.stderr or "agent_desk failed")[:500]}
    raw = (r.stdout or "").strip()
    brace = raw.find("{")
    if brace >= 0:
        return json.loads(raw[brace:])
    return json.loads(raw)


def _save_pending(data: dict) -> None:
    path = adc.DESK_PENDING_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    row = dict(data)
    row["pending_saved_at"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(row, f, ensure_ascii=False, indent=2)


def _trigger_llm_job() -> None:
    subprocess.Popen(
        ["hermes", "cron", "run", adc.DESK_LLM_CRON_ID],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main():
    data = _run_desk()
    _save_pending(data)
    if data.get("needs_hermes"):
        _trigger_llm_job()
        print(json.dumps({"ok": True, "needs_hermes": True, "triggered": adc.DESK_LLM_CRON_ID}))
    else:
        # no_agent 模式：空输出即可，调度器不唤 LLM
        print(json.dumps({"ok": True, "needs_hermes": False, "silent": True}))


if __name__ == "__main__":
    main()
