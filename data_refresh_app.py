#!/config/quant_env/bin/python3
"""
盘中/收盘数据刷新（P2）— 仅跑 apps/*，无 LLM。
stdout JSON 供 Cron 静默确认：ok=true 即成功。
"""
import json
import os
import subprocess
import sys

VENV_PY = "/config/quant_env/bin/python3"
BASE = "/config/quant_scripts/apps"
DATA = "/config/quant_scripts/data"

sys.path.insert(0, "/config/quant_scripts")
from cron_refresh_config import EMERGENCY_FILE, EMERGENCY_SIGNAL  # noqa: E402


def _push_refresh_alert(slot: str, message: str) -> None:
    """失败时写紧急通道（guard/紧急 cron 可读），替代原 LLM 推③系统状态。"""
    body = f"③ 数据刷新失败 [{slot}]\n{message}"[:2000]
    try:
        with open(EMERGENCY_SIGNAL, "w", encoding="utf-8") as f:
            f.write("REFRESH_FAIL")
        with open(EMERGENCY_FILE, "w", encoding="utf-8") as f:
            f.write(body)
    except OSError:
        pass

SLOTS = {
    "flash": ("flash.py", "flash_output.json"),
    "midday": ("midday.py", "midday_output.json"),
    "noon": ("noon.py", "noon_output.json"),
    "afternoon": ("afternoon.py", "afternoon_output.json"),
    "close": ("close.py", "close_output.json"),
}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: data_refresh_app.py <flash|midday|noon|afternoon|close>"}))
        sys.exit(1)
    slot = sys.argv[1].strip().lower()
    if slot not in SLOTS:
        print(json.dumps({"error": f"unknown slot: {slot}"}))
        sys.exit(1)
    app_name, out_name = SLOTS[slot]
    app = os.path.join(BASE, app_name)
    out = os.path.join(DATA, out_name)
    extra = []
    if "--quick" in sys.argv and slot == "afternoon":
        extra = ["--quick"]

    cmd = [VENV_PY, app, "--save", out] + extra
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    payload = {
        "phase": "data_refresh",
        "slot": slot,
        "ok": r.returncode == 0,
        "output_path": out,
        "needs_hermes": False,
        "instruction": "本 job 仅刷新 JSON，Hermes 应完全静默（不解读、不推长文）。",
    }
    if r.returncode != 0:
        payload["stderr"] = (r.stderr or "")[:800]
        _push_refresh_alert(slot, payload["stderr"] or f"exit {r.returncode}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(r.returncode)

    if os.path.isfile(out):
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        payload["recommendation"] = data.get("recommendation")
        payload["generated_at"] = data.get("generated_at")
        if slot == "afternoon":
            t15 = data.get("tier15_deploy_scan") or {}
            payload["tier15_triggered"] = t15.get("triggered")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
