#!python3
"""
盘中/收盘数据刷新（P2）— 仅跑 apps/*，无 LLM。
stdout JSON 供 Cron 静默确认：ok=true 即成功。
"""
import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, '/root/ai_trading_package/quant/quant_scripts')
from system_config import cfg
from cron_refresh_config import EMERGENCY_FILE, EMERGENCY_SIGNAL

VENV_PY = cfg.python
BASE = cfg.path.apps_dir
DATA = cfg.data_dir


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

# ── 盘中报告 webhook 推送（T1.12 修复）──
def _load_webhook_url() -> str:
    env_path = cfg.path.hermes_env
    if os.path.isfile(env_path):
        for line in open(env_path, encoding="utf-8").read().splitlines():
            if line.startswith("WECHAT_WEBHOOK_URL="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("WECHAT_WEBHOOK_URL", "")


def _send_webhook_report(slot: str, out_path: str) -> bool:
    """盘中报告生成后通过 webhook 推送，替代 LLM 延迟投递。"""
    url = _load_webhook_url()
    if not url:
        return False
    try:
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False

    now = datetime.now().strftime("%m-%d %H:%M")
    label = {"flash": "开盘闪电战", "midday": "盘中快照", "noon": "午间总结",
             "afternoon": "下午速报", "close": "收盘总结"}.get(slot, slot)
    recommendation = data.get("recommendation", "?")
    holdings = data.get("holdings", [])

    lines = [f"【{label}】{now} CST", f"建议: {recommendation}", ""]
    for h in holdings[:12]:
        code = h.get("code", "")
        name = h.get("name", "")
        price = h.get("price", 0)
        pct = h.get("change_pct", h.get("gap_pct", 0))
        lines.append(f"{code} {name} ¥{price:.2f} {pct:+.1f}%")
    body = "\n".join(lines)[:4000]
    payload = json.dumps({"msgtype": "markdown", "markdown": {"content": body}}, ensure_ascii=False)
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", url, "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=10)
        return '"errcode":0' in r.stdout
    except Exception:
        return False


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
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
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
        # ── T1.12: 即使失败也尝试推送已有文件 ──
        if os.path.isfile(out):
            _send_webhook_report(slot, out)
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
        # ── T1.12: 盘中报告 webhook 即时推送 ──
        pushed = _send_webhook_report(slot, out)
        payload["webhook_pushed"] = pushed
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
