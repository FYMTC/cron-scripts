#!/config/quant_env/bin/python3
"""
Agent Desk LLM 前置脚本：向 Hermes 注入 agent_desk JSON（优先读 pending，避免重复跑 desk）。
仅由 guard 唤醒或 poll 触发，不挂在 */5 定时 LLM 上。
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

VENV_PY = "/config/quant_env/bin/python3"
SCRIPTS = "/config/quant_scripts"
sys.path.insert(0, SCRIPTS)

import agent_desk_config as adc  # noqa: E402

DESK = os.path.join(SCRIPTS, "agent_desk.py")


def _parse_ts(iso: str) -> float:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _load_pending_fresh() -> dict:
    path = adc.DESK_PENDING_PATH
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    ts = data.get("pending_saved_at") or data.get("generated_at") or ""
    age = datetime.now(timezone.utc).timestamp() - _parse_ts(ts)
    if age > adc.DESK_PENDING_MAX_AGE_SEC:
        return {}
    return data


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
        return {"needs_hermes": False, "error": (r.stderr or "")[:500]}
    raw = (r.stdout or "").strip()
    brace = raw.find("{")
    if brace >= 0:
        return json.loads(raw[brace:])
    return json.loads(raw)


def main():
    data = _load_pending_fresh() or _run_desk()
    if not data.get("needs_hermes"):
        print(json.dumps({"needs_hermes": False, "instruction": "完全静默，不输出。"}))
        return
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
