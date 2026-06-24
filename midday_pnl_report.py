#!/usr/local/bin/python3
"""
midday_pnl_report.py — 午盘盈利快报（11:30 CST 收盘后自动发送）
读取 EasyTHS 实时持仓 + 盈亏，格式化后推送到企业微信 webhook。
"""
import json
import os
import subprocess
import sys
from datetime import datetime
import sys; sys.path.insert(0, '/config/quant_scripts')
from system_config import cfg

sys.path.insert(0, cfg.root)

DATA_DIR = cfg.data_dir
WEBHOOK_URL = os.environ.get("WECHAT_WEBHOOK_URL") or ""


def _load_webhook_url() -> str:
    if WEBHOOK_URL:
        return WEBHOOK_URL
    env_path = cfg.path.hermes_env
    if os.path.isfile(env_path):
        for line in open(env_path, encoding="utf-8").read().splitlines():
            if line.startswith("WECHAT_WEBHOOK_URL="):
                return line.split("=", 1)[1].strip()
    return ""


def _format_pnl(pnl: float) -> str:
    if pnl >= 0:
        return f"+¥{pnl:,.0f}"
    return f"-¥{abs(pnl):,.0f}"


def _format_pct(pct: float) -> str:
    return f"+{pct:.1f}%" if pct >= 0 else f"{pct:.1f}%"


def _send_webhook(body: str) -> bool:
    url = _load_webhook_url()
    if not url:
        print("[midday] no webhook URL configured")
        return False
    payload = json.dumps(
        {"msgtype": "markdown", "markdown": {"content": body[:4000]}},
        ensure_ascii=False,
    )
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", url,
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=10,
        )
        return '"errcode":0' in r.stdout
    except Exception:
        return False


def main():
    from trade_account_context import load_portfolio_truth  # type: ignore[import-not-found]
    from market_data import fetch_quotes_batch  # type: ignore[import-not-found]

    pf = load_portfolio_truth()
    positions = pf.get("positions", {})
    cash = pf.get("cash", 0)
    total = pf.get("total_assets", 0)

    if not positions:
        print("[midday] no positions — skipping")
        return

    codes = list(positions.keys())
    quotes = {}
    try:
        quotes = fetch_quotes_batch(codes)
    except Exception:
        pass

    now = datetime.now().strftime("%m-%d %H:%M")
    lines = [
        f"【午盘盈利快报】{now} CST",
        f"",
        f"| 标的 | 持仓 | 成本 | 现价 | 市值 | 盈亏 | 盈亏% |",
        f"|:---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    total_pnl = 0.0
    total_cost = 0.0
    total_mv = 0.0
    for code, pos in sorted(positions.items()):
        name = pos.get("name", code)
        shares = pos.get("shares", 0)
        cost = pos.get("cost", 0)
        price = pos.get("current_price", 0)
        mv = pos.get("market_value", shares * price)
        pnl = pos.get("profit", (price - cost) * shares if price and cost else 0)

        q = quotes.get(code, {})
        if q:
            live_price = q.get("price")
            if live_price and live_price > 0:
                price = live_price
                mv = shares * price
                pnl = (price - cost) * shares

        total_mv += mv
        total_cost += shares * cost
        total_pnl += pnl

        lines.append(
            f"| {name}({code}) | {shares} | {cost:.2f} | {price:.2f} | {mv:,.0f} | "
            f"{_format_pnl(pnl)} | {_format_pct((price-cost)/cost*100 if cost>0 else 0.0)} |"
        )

    total_pnl_pct = total_pnl / total_cost * 100 if total_cost > 0 else 0
    lines.extend([
        f"",
        f"| | | | | | | |",
        f"| **合计** | | | | **{total_mv:,.0f}** | **{_format_pnl(total_pnl)}** | **{_format_pct(total_pnl_pct)}** |",
        f"",
        f"💰 现金: ¥{cash:,.0f} | 总资产: ¥{cash + total_mv:,.0f}",
        f"📊 仓位: {(total_mv/(cash+total_mv)*100) if (cash+total_mv)>0 else 0:.1f}%",
    ])

    # ── Single-stock concentration check ──
    grand_total = cash + total_mv if (cash + total_mv) > 0 else 1
    for code in sorted(positions, key=lambda c: positions[c].get("market_value", 0), reverse=True):
        mv = positions[code].get("market_value", 0)
        pct = mv / grand_total * 100
        if pct > 20:
            lines.append(f"⚠️ {code} 集中度 {pct:.1f}% 超过 20% 红线")

    # ── check EasyTHS live server open orders (2026-06-06: live_easyths 替代 paper) ──
    try:
        import ths_trade_executor as ex  # type: ignore[import-not-found]
        from trade_accounts import desk_primary_account, get_account  # type: ignore[import-not-found]

        acct_id = desk_primary_account() or "live_easyths"
        acct = get_account(acct_id) or {}
        eas_cfg_path = (acct.get("execution") or {}).get("easyths_config")
        if not eas_cfg_path:
            raise RuntimeError(f"account {acct_id} has no easyths_config")
        cfg = ex.load_trade_config(eas_cfg_path)
        client = ex.build_client(cfg)
        resp = client.query_orders() or {}
        orders = ((resp.get("data") or {}).get("orders")) or []
        pending = sum(
            1 for o in orders
            if isinstance(o, dict) and str(o.get("status", "")).lower() not in ("已成", "已撤", "部撤")
        )
        if pending > 0:
            lines.append(f"\n⚠️ EasyTHS live 有 {pending} 笔挂单未成交")
    except Exception as exc:
        print(f"[midday] WARN live order_query failed: {exc}", file=__import__("sys").stderr)

    body = "\n".join(lines)
    ok = _send_webhook(body)
    print(f"[midday] report sent: {ok} ({len(body)} chars)")
    print(body)


if __name__ == "__main__":
    main()
