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
    total_value = 0.0
    for h in (holdings or [])[:limit]:
        code = h.get("code", "?")
        name = h.get("name", code)
        sh = h.get("shares", 0)
        price = h.get("price", 0)
        mv = price * sh
        total_value += mv
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


def _fmt_explainability(plan: dict) -> List[str]:
    constraints = ((plan or {}).get("explainability") or {}).get("constraints") or {}
    if not constraints:
        return []
    lines = []
    if constraints.get("summary"):
        lines.append(f"- {constraints.get('summary')}")
    for factor in (constraints.get("blocking_factors") or [])[:3]:
        msg = factor.get("message") or factor.get("rule")
        required = factor.get("required")
        if required:
            lines.append(f"- 阻塞因子 {factor.get('rule', '?')}: {msg}；要放行为 {required}")
        else:
            lines.append(f"- 阻塞因子 {factor.get('rule', '?')}: {msg}")
    if constraints.get("next_best_action"):
        lines.append(f"- 次优动作: {constraints.get('next_best_action')}")
    return lines


def _fmt_concentration(holdings: List[dict], cash: float, total_assets: float) -> List[str]:
    if not holdings or total_assets <= 0:
        return []
    lines = []
    for h in holdings:
        code = h.get("code", "?")
        name = h.get("name", code)
        sh = h.get("shares", 0)
        price = h.get("price", 0)
        mv = price * sh
        pct = mv / total_assets * 100 if total_assets > 0 else 0
        flag = "🔴" if pct > 50 else ("🟡" if pct > 20 else "✅")
        lines.append(f"- {flag} {name}({code}): {sh}股 × ¥{price} = ¥{mv:,.0f} → **{pct:.1f}%**")
    cash_pct = cash / total_assets * 100 if total_assets > 0 else 0
    lines.append(f"- 💵 现金: ¥{cash:,.0f} ({cash_pct:.1f}%)")
    over_20 = [h for h in holdings if (h.get("price", 0) * h.get("shares", 0)) / total_assets > 0.20]
    if over_20:
        lines.append(f"- ⛔ **单标超标(>20%)**: {len(over_20)} 只，须优先评估减仓")
    return lines


def _fmt_model_risk(plan_or_review: dict) -> List[str]:
    ledger = (plan_or_review or {}).get("model_risk_ledger") or {}
    summary = ledger.get("summary") or {}
    items = ledger.get("items") or []
    if not summary and not items:
        return []
    lines = [
        f"- 模型/特征组件: {summary.get('model_count', len(items))} 个",
        f"- 降级组件: {summary.get('degraded_count', 0)} 个",
    ]
    degraded_items = summary.get("degraded_items") or []
    if degraded_items:
        lines.append(f"- 当前降级: {', '.join(degraded_items[:5])}")
    for item in items[:4]:
        if item.get("degraded"):
            lines.append(
                f"- {item.get('name')}: {item.get('status')} ({item.get('fallback_reason') or 'unknown'})"
            )
    return lines


def morning_digest() -> dict:
    m = _load("morning_output.json")
    plan = _load("plan_bundle.json")
    if not m:
        return {"error": "morning_output.json missing", "push_wechat_required": False}

    constraints = m.get("constraints") or []
    cands = m.get("candidates") or plan.get("candidates_top") or []
    sig = plan.get("signal_auto_generate") or m.get("signal_auto_generate") or {}

    parts = [
        f"【②工作报告-早计划】{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**总建议**: {m.get('recommendation', '?')}",
        f"现金 ¥{m.get('cash')} | 总资产 ¥{m.get('total_assets')} | "
        f"仓位 {m.get('position_ratio_pct', '?')}%",
    ]

    holdings = m.get("holdings") or []
    parts.append(_section("持仓", _fmt_holdings(holdings)))
    cash = m.get("cash") or 0
    total = m.get("total_assets") or 0
    parts.append(_section("集中度分析", _fmt_concentration(holdings, cash, total)))
    parts.append(_section("硬约束", _fmt_constraints(constraints)))
    parts.append(_section("解释层（为什么暂不放行）", _fmt_explainability(plan)))
    parts.append(_section("模型风险台账", _fmt_model_risk(plan)))
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

    # ── deployment plan ──
    dp = m.get("deployment_plan") or {}
    if dp:
        dp_lines = [
            f"- 事件级别: **{dp.get('event_level', '?')}** → {dp.get('tier_description', '')}",
            f"- 目标仓位: ≤{dp.get('target_exposure_pct', '?')}% (可部署 ¥{dp.get('deployable_cash', 0):,.0f})",
            f"- 当前仓位: {dp.get('current_exposure_pct', '?')}%",
        ]
        gap = dp.get("deployment_gap", 0)
        if gap and gap > 0:
            dp_lines.append(f"- 部署缺口: ¥{gap:,.0f}")
        dp_lines.append(f"- 预留现金: ¥{dp.get('reserve_cash', 0):,.0f} ({dp.get('min_cash_pct', dp.get('event_level','') and 20)}%下限)")
        blocked = dp.get("candidates_blocked") or []
        if blocked:
            dp_lines.append(f"- 候选筛选: {dp.get('candidates_considered','?')} 个候选，{dp.get('candidates_passed','?')} 个通过，{len(blocked)} 个被拒")
            for b in blocked[:5]:
                dp_lines.append(f"  · {b.get('code')}: {', '.join(b.get('reasons', [])[:3])}")
        parts.append(_section("仓位部署计划", dp_lines))

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
            "以 wechat_work_report_body 为底稿润色/扩展后作为最终回复（可更详细，禁止删节约束/宏观/持仓/解释层）；"
            "deliver=origin 自动推微信。禁止跳过推送。禁止修脚本报错除非 script 失败。"
        ),
    }


def _fmt_account_runtime(review: dict) -> List[str]:
    runtime = (review or {}).get("account_runtime") or {}
    primary = runtime.get("primary_account") or {}
    if not runtime:
        return []
    lines = [
        f"- 运行模式: {runtime.get('runtime_mode', '?')}",
        f"- 主账户: {runtime.get('desk_primary_account', '?')}",
    ]
    if primary.get("label"):
        lines.append(f"- 主链标签: {primary.get('label')}")
    if primary.get("position_count") is not None:
        lines.append(f"- 主账户持仓数: {primary.get('position_count')}")
    if runtime.get("special_mode"):
        lines.append("- special_mode: 已启用多账户特殊模式")
    return lines


def night_digest() -> dict:
    n = _load("night_output.json")
    r = _load("review_bundle.json")
    if not n and not r:
        return {"error": "night_output.json and review_bundle missing", "push_wechat_required": False}

    audit = r.get("signal_audit") or {}
    summary = audit.get("summary") or {}
    night = n or {}

    # ── Holdings: prefer night_output, fallback to morning_output ──
    holdings = night.get("holdings") or []
    cash = night.get("cash", 0)
    total = night.get("total_assets", 0)
    morning = {}
    if not holdings:
        # Try reading morning_output for the latest holdings snapshot
        morning = _load("morning_output.json")
        holdings = morning.get("holdings") or []
        cash = morning.get("cash", cash)
        total = morning.get("total_assets", total)

    parts = [
        f"【②工作报告-晚复盘】{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**收盘建议**: {night.get('recommendation', r.get('night_summary', {}).get('recommendation', '?'))}",
    ]

    if total > 0 and cash > 0:
        parts.append(f"现金 ¥{cash:,.0f} | 总资产 ¥{total:,.0f} | 仓位 {(1-cash/total)*100 if total>0 else 0:.1f}%")

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

    parts.append(_section("收盘持仓", _fmt_holdings(holdings)))
    parts.append(_section("集中度分析", _fmt_concentration(holdings, cash, total)))
    parts.append(_section("账户运行态", _fmt_account_runtime(r)))

    # ── De-risk / blocked opportunities ──
    de_risk = night.get("de_risk_plan") or morning.get("de_risk_plan") or {}
    dr_actions = de_risk.get("actions") or []
    if dr_actions:
        lines = [f"- de_risk_plan 包含 {len(dr_actions)} 笔减仓候选:"]
        for a in dr_actions[:5]:
            lines.append(f"  · {a.get('name')}({a.get('code')}) SELL {a.get('shares')}股 — {a.get('reason', '')[:60]}")
        parts.append(_section("组合减仓计划", lines))

    # ── Strategy validation ──
    sv = night.get("strategy_validation") or {}
    if sv:
        parts.append(_section("策略验证", [
            f"- 待验证候选: {sv.get('pending_candidates', sv.get('candidates_count', '?'))} 只",
        ]))

    # ── CVRF reflection ──
    cvrf = r.get("cvrf_stdout_preview") or ""
    if cvrf and len(cvrf) > 50:
        parts.append(_section("CVRF 反思", [f"- {cvrf[:300]}" + ("…" if len(cvrf) > 300 else "")]))

    parts.append(_section("模型风险台账", _fmt_model_risk(r)))
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
        ok_lines = [f"- v5_self_check: {'PASS' if sc.get('ok') else 'FAIL'}"]
        if not sc.get("ok"):
            ok_lines.append(f"- 失败项: {', '.join((sc.get('checks', {}).get('unittest', {}).get('failure_names') or [])[:5])}")
        parts.append(_section("系统自检", ok_lines))

    cands = night.get("candidates") or []
    if cands:
        parts.append(_section("明日关注候选", _fmt_candidates(cands, 5)))

    parts.append(
        "\n### 复盘要点\n"
        "- 将可复用教训写入 stock_kb insights（供明日 Plan/Desk）。\n"
        "- 假突破/冲顶未止盈等须写清标的与日期。\n"
        "- 明日盘前先读 screener_top15 + cron_state 宏观档位。\n"
        "- 若存在 de_risk_plan 减仓候选：明日 agent_desk 将自动生成 SELL 请示，无需人工判断。"
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
