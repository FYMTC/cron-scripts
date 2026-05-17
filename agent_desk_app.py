#!/config/quant_env/bin/python3
"""
Agent Desk 薄封装 — 消费 agent_queue，stdout JSON 供 Hermes。
无待分析任务时 exit 0 且 needs_hermes=false（Hermes 应完全静默）。
"""
import json
import subprocess
import sys

VENV_PY = "/config/quant_env/bin/python3"
DESK = "/config/quant_scripts/agent_desk.py"


def main():
    r = subprocess.run(
        [VENV_PY, DESK, "--json", "--max", "5"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if r.stderr:
        sys.stderr.write(r.stderr)
    if r.returncode != 0:
        print(
            json.dumps(
                {"needs_hermes": False, "error": r.stderr[:500] or "agent_desk failed"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        print(r.stdout)
        sys.exit(0)

    print(json.dumps(data, ensure_ascii=False, indent=2))
    if not data.get("needs_hermes"):
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
