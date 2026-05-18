#!/config/quant_env/bin/python3
"""
工作报告 digest（P3）— 从已落盘 JSON 生成详细工作报告底稿，供 Hermes 润色后推微信。

v5.5：取消 400/500 字硬截断；morning_plan_app / review_app 在代码中自动调用。
"""
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

DATA = "/config/quant_scripts/data"
# 单条微信建议上限（字符）；底稿可更长，Hermes 润色时可拆条
SOFT_MAX_CHARS = 6000


def _load(name: str) -> dict:
    p = os.path.join(DATA, name)
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as f:
        text = f.read()
    brace = text.find("{")
    if brace >= 0:
        return json.loads(text[brace:])
    return json.loads(text)


def _section(title: str, lines: List[str]) -> str:
    body = [ln for ln in lines if ln]
    if not body:
        return ""
    return f"\n### {title}\n" + "\n".join(body)


def _fmt_holdings(holdings: List[dict], limit: int = 12) -> List[str]:
    lines = []
    for h in (holdings or [])[:limit]:
        code = h.get("code", "?")
        name = h.get("name", code)
        sh = h.get("shares", 0)
        price = h.get("price", 0)
        pnl = h.get("pnl")
        pnl_pct = h.get("pnl_pct")
        extra = ""
        if pnl is not None:
            extra = f" 浮盈{pnl:+.0f}({pnl_pct:+.1f}%)" if pnl_pct is not None else f" 浮盈{pnl:+.0f}"
        elif h.get("error"):
            extra = f" [{h.get('error')}]"
        lines.append(f"- {name}({code}) {sh}股 @¥{price}{extra}")
    if len(holdings or []) > limit:
        lines.append(f"- …共 {len(holdings)} 只，已列前 {limit}")
    return lines


def _fmt_constraints(constraints: List[dict]) -> List[str]:
    lines = []
    for c in constraints or []:
        mark = "✓" if c.get("pass") else "✗"
        lines.append(f"- [{mark}] {c.get('check', '?')}: {c.get('message', '')}")
    return lines


def _fmt_event_risk(m: dict) -> List[str]:
    ev = m.get("event_risk") or {}
    if not ev:
        return []
    lines = [
        f"- 档位: **{ev.get('event_level', '?')}** → 建议收紧为 {ev.get('recommendation_override', '?')}",
    ]
    hits = ev.get("keyword_hits") or []
    if hits:
        lines.append(f"- 命中: {', '.join(hits[:8])}" + ("…" if len(hits) > 8 else ""))
    pb = ev.get("playbook") or {}
    if pb.get("message"):
        lines.append(f"- Playbook: {pb.get('message')}")
    if m.get("macro_block_new_buy"):
        lines.append("- ⛔ 宏观层：**禁止新开仓**")
    dr = m.get("de_risk_plan") or {}
    actions = dr.get("actions") or []
    if actions:
        lines.append(f"- 组合减仓计划: {len(actions)} 笔 SELL 候选（须走 gate+请示）")
        for a in actions[:5]:
            lines.append(
                f"  · {a.get('name')}({a.get('code')}) 卖{a.get('shares')}股 "
                f"@¥{a.get('price')} — {a.get('reason', '')[:60]}"
            )
    return lines


def _fmt_candidates(cands: List[dict], limit: int = 8) -> List[str]:
    lines = []
    for i, c in enumerate((cands or [])[:limit], 1):
        lines.append(
            f"- #{i} {c.get('name', c.get('code'))}({c.get('code')}) "
            f"分={c.get('composite_score', '?')} 20d={c.get('mom_20d', '?')}%"
        )
    return lines


def morning_digest() -> dict:
    m = _load("morning_output.json")
    plan = _load("plan_bundle.json")
    if not m:
        return {"error": "morning_output.json missing", "push_wechat_required": False}

    constraints = m.get("constraints") or []
    constraints_fail = [c for c in constraints if not c.get("pass")]
    cands = m.get("candidates") or plan.get("candidates_top") or []
    sig = plan.get("signal_auto_generate") or m.get("signal_auto_generate") or {}

    parts = [
        f"【②工作报告-早计划】{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**总建议**: {m.get('recommendation', '?')}",
        f"现金 ¥{m.get('cash')} | 总资产 ¥{m.get('total_assets')} | "
        f"仓位 {m.get('position_ratio_pct', '?')}%",
    ]

    parts.append(_section("持仓", _fmt_holdings(m.get("holdings") or [])))
    parts.append(_section("硬约束", _fmt_constraints(constraints)))
    parts.append(_section("宏观 / 地缘 (R2)", _fmt_event_risk(m)))

    qs = m.get("quant_summary") or {}
    if qs:
        parts.append(
            _section(
                "组合量化摘要",
                [
                    f"- 平均 CVaR: {qs.get('avg_cvar')}%",
                    f"- 最差 CVaR: {qs.get('worst_cvar')}%",
                    f"- 平均 GARCH 年化波动: {qs.get('avg_garch_vol')}%",
                ],
            )
        )

    parts.append(_section("昨夜选股 Top 候选", _fmt_candidates(cands)))
    if sig:
        parts.append(
            _section(
                "今日注册信号",
                [
                    f"- total_signals: {sig.get('total_signals', sig.get('registered', '?'))}",
                    f"- tier_a/b: {sig.get('tier_a', '?')} / {sig.get('tier_b', '?')}",
                ],
            )
        )

    parts.append(
        "\n### 今日执行要点\n"
        "- 盘中仅 **Agent Desk** 唤醒后做 Decide；买卖须 **trade_outbox 请示**（附 lineage）。\n"
        "- 若 recommendation=BLOCKED：禁止新开仓，优先处理 de_risk_plan 减仓候选。\n"
        "- 刷新档 cron 静默，勿期待盘中长报告。"
    )

    text = "\n".join(p for p in parts if p).strip()
    if len(text) > SOFT_MAX_CHARS:
        text = text[: SOFT_MAX_CHARS - 20] + "\n…(底稿过长已软截断，Hermes 可引用 plan_bundle 补充)"

    return {
        "phase": "digest_morning",
        "digest_text": text,
        "wechat_work_report_body": text,
        "push_wechat_required": True,
        "wechat_report_type": "②工作报告-早计划",
        "needs_hermes": True,
        "instruction": (
            "以 wechat_work_report_body 为底稿润色/扩展后作为最终回复（可更详细，禁止删节约束/宏观/持仓）；"
            "deliver=origin 自动推微信。禁止跳过推送。禁止修脚本报错除非 script 失败。"
        ),
    }


def night_digest() -> dict:
    n = _load("night_output.json")
    r = _load("review_bundle.json")
    if not n and not r:
        return {"error": "night_output.json and review_bundle missing", "push_wechat_required": False}

    audit = r.get("signal_audit") or {}
    summary = audit.get("summary") or {}
    night = n or {}

    parts = [
        f"【②工作报告-晚复盘】{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**收盘建议**: {night.get('recommendation', r.get('night_summary', {}).get('recommendation', '?'))}",
    ]

    pnl = night.get("pnl_summary") or {}
    if pnl:
        parts.append(
            _section(
                "当日盈亏",
                [
                    f"- 持仓 {pnl.get('positions')} 只",
                    f"- 浮动盈亏合计 ¥{pnl.get('total_pnl')}",
                    f"- 市值 ¥{pnl.get('market_value')} / 成本 ¥{pnl.get('cost_basis')}",
                ],
            )
        )

    parts.append(_section("收盘持仓", _fmt_holdings(night.get("holdings") or [])))
    parts.append(_section("宏观 / 地缘 (R2)", _fmt_event_risk(night)))

    if summary:
        parts.append(
            _section(
                "信号审计",
                [
                    f"- 触发 {summary.get('triggers', summary.get('trigger', 0))} 次",
                    f"- 分析 {summary.get('analyze', summary.get('analyses', 0))} 次",
                    f"- 决策 {summary.get('decisions', 0)} 次",
                ],
            )
        )

    sc = r.get("steps", {}).get("v5_self_check") or {}
    if sc:
        parts.append(
            _section(
                "系统自检",
                [
                    f"- v5_self_check: {'PASS' if sc.get('ok') else 'FAIL'}",
                ]
                + (
                    [f"- 失败项: {', '.join((sc.get('checks', {}).get('unittest', {}).get('failure_names') or [])[:5])}"]
                    if not sc.get("ok")
                    else []
                ),
            )
        )

    cands = night.get("candidates") or []
    if cands:
        parts.append(_section("明日关注候选", _fmt_candidates(cands, 5)))

    parts.append(
        "\n### 复盘要点\n"
        "- 将可复用教训写入 stock_kb insights（供明日 Plan/Desk）。\n"
        "- 假突破/冲顶未止盈等须写清标的与日期。\n"
        "- 明日盘前先读 screener_top15 + cron_state 宏观档位。"
    )

    text = "\n".join(p for p in parts if p).strip()
    if len(text) > SOFT_MAX_CHARS:
        text = text[: SOFT_MAX_CHARS - 20] + "\n…(底稿过长已软截断)"

    out: Dict[str, Any] = {
        "phase": "digest_night",
        "digest_text": text,
        "wechat_work_report_body": text,
        "push_wechat_required": True,
        "wechat_report_type": "②工作报告-晚复盘",
        "review_bundle_path": r.get("review_bundle_path") or os.path.join(DATA, "review_bundle.json"),
        "needs_hermes": True,
        "instruction": (
            "以 wechat_work_report_body 为底稿写详细晚复盘（可加长）；"
            "deliver=origin 自动推微信。v5_self_check 失败时另推③系统状态一条。"
        ),
    }
    if not sc.get("ok", True):
        out["also_push_system_status"] = True
    return out


def main():
    phase = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if phase == "morning":
        out = morning_digest()
    elif phase in ("night", "review"):
        out = night_digest()
    else:
        out = {"error": "usage: digest_app.py morning|night"}
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
