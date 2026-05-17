#!/config/quant_env/bin/python3
"""每晚系统自检薄封装 → stdout JSON（并入 review_bundle）。"""
import json
import subprocess
import sys

VENV_PY = "/config/quant_env/bin/python3"
CHECK = "/config/quant_scripts/v5_self_check.py"


def main():
    r = subprocess.run([VENV_PY, CHECK, "--json"], capture_output=True, text=True, timeout=120)
    if r.stdout:
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            data = {"ok": False, "raw": r.stdout[:500]}
    else:
        data = {"ok": False, "error": r.stderr[:500] if r.stderr else "no output"}
    data["needs_hermes"] = not data.get("ok", False)
    if not data.get("ok"):
        data["instruction"] = (
            "v5_self_check 失败：请在 review 中推③系统状态摘要，并列出 failure_names / missing paths。"
        )
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(0 if data.get("ok") else 1)


if __name__ == "__main__":
    main()
