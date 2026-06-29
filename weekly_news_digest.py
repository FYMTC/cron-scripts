#!/usr/bin/env python3
"""
每周中外新闻概览 — 周六推送企业微信
聚焦：时政/金融/科技/经济

数据源：
  - Twitter/X: 全球突发 + 宏观讨论
  - Reddit: r/worldnews + r/technology + r/economics + r/stocks
  - 雪球: A股热帖聚焦
  - Web: 补充中文时政/财经头条
"""
import json
import re
import subprocess
import sys
import os
from datetime import datetime, timedelta

AGENT_REACH_VENV = os.path.expanduser("~/.agent-reach-venv")
BIN = f"{AGENT_REACH_VENV}/bin"
PYTHON = f"{BIN}/python3"
WEEK_AGO = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")


def _run(cmd, timeout=25):
    env = os.environ.copy()
    env["PATH"] = f"{BIN}:{env.get('PATH', '')}"
    try:
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=timeout, env=env)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def fetch_twitter_news(n=15):
    """Twitter 首页 Feed — 提取新闻/宏观相关内容"""
    out = _run(f"twitter feed -n {n}", timeout=30)
    items = []
    if out:
        for line in out.split('\n'):
            line = line.strip()
            if line.startswith('text:') and len(line) > 20:
                text = line[5:].strip().replace('\n', ' ')[:250]
                items.append(text)
    return items


def fetch_reddit_topics():
    """Reddit 时政/科技/经济/金融板块"""
    subs = {
        "worldnews": "🌍 国际时政",
        "technology": "💻 科技",
        "economics": "📊 经济",
        "stocks": "📈 金融市场",
    }
    results = {}
    for sub, label in subs.items():
        out = _run(f"rdt sub {sub} --limit 6", timeout=30)
        posts = []
        if out:
            for line in out.split('\n'):
                m = re.search(r'"title":\s*"([^"]+)"', line)
                if m:
                    posts.append(m.group(1)[:150])
        results[label] = posts[:5] if posts else ["(无数据)"]
    return results


def fetch_xueqiu_digest():
    """雪球 A 股热门帖 — 时政/金融/科技/经济相关"""
    script = (
        f'import sys, json\n'
        f'sys.path.insert(0, "{AGENT_REACH_VENV}/lib/python3.12/site-packages")\n'
        f'from agent_reach.channels.xueqiu import XueqiuChannel\n'
        f'ch = XueqiuChannel()\n'
        f'r = {{}}\n'
        f'try:\n'
        f'    posts = ch.get_hot_posts(limit=15)\n'
        f'    r["posts"] = [{{"t": p.get("title","?")[:100], "r": p.get("reply_count",0)}} for p in (posts or [])[:15]]\n'
        f'except Exception as e:\n'
        f'    r["err"] = str(e)[:100]\n'
        f'print(json.dumps(r, ensure_ascii=False))\n'
    )
    out = _run(f'{PYTHON} -c \'{script}\'', timeout=30)
    try:
        return json.loads(out) if out else {}
    except Exception:
        return {}


def filter_relevant(posts, keywords_cn, keywords_en):
    """筛选与主题相关的帖子"""
    relevant = []
    for p in posts:
        text = p.lower()
        if any(kw.lower() in text for kw in keywords_cn + keywords_en):
            relevant.append(p)
    return relevant[:8]


def format_markdown(twitter, reddit, xueqiu):
    """格式化为企业微信 Markdown"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# 📰 每周中外新闻概览",
        f"## {now} 发布 | 覆盖 {WEEK_AGO} ~ 今",
        "",
    ]

    # ── 1. 全球要闻 (Twitter) ──
    lines.append("---")
    lines.append("## 🌐 全球要闻 (Twitter/X)")
    keywords_news = ["china", "中国", "trump", "特朗普", "tariff", "关税", "fed", "美联储",
                     "war", "战争", "peace", "和平", "policy", "政策", "congress", "国会",
                     "president", "总统", "election", "选举", "nato", "北约", "eu", "欧盟",
                     "ukraine", "乌克兰", "russia", "俄罗斯", "taiwan", "台湾",
                     "beijing", "北京", "shanghai", "上海", "trade", "贸易",
                     "crash", "暴跌", "surge", "暴涨", "market", "市场", "stock", "股票"]
    news_items = filter_relevant(twitter, keywords_news, keywords_news)
    for i, t in enumerate(news_items[:10], 1):
        lines.append(f"{i}. {t[:180]}")
    if not news_items:
        lines.append("> 本周 Twitter 无匹配时政/财经内容")

    # ── 2. Reddit 板块 ──
    lines.append("")
    lines.append("---")
    lines.append("## 🔴 Reddit 热门讨论")
    for label, posts in reddit.items():
        lines.append(f"### {label}")
        for i, p in enumerate(posts[:4], 1):
            lines.append(f"{i}. {p[:150]}")
        lines.append("")

    # ── 3. A股社区 (雪球) ──
    xq_posts = xueqiu.get("posts", [])
    lines.append("---")
    lines.append("## 📈 A股社区热议 (雪球)")
    keywords_a = ["政策", "关税", "科技", "AI", "芯片", "半导体", "新能源", "医药",
                  "美联储", "加息", "降息", "特朗普", "贸易战", "经济", "GDP", "CPI",
                  "地产", "楼市", "金融", "银行", "利率", "汇率", "人民币", "美元",
                  "改革", "监管", "产业", "制造", "出口", "消费"]
    a_items = []
    for p in xq_posts:
        title = p.get("t", "")
        if any(kw in title for kw in keywords_a):
            a_items.append(f'{p["t"]}（{p.get("r",0)}评）')
    for i, t in enumerate(a_items[:8], 1):
        lines.append(f"{i}. {t[:150]}")
    if not a_items:
        for i, p in enumerate(xq_posts[:5], 1):
            lines.append(f"{i}. {p.get('t','?')[:120]}")

    # ── 4. 本周关键词 ──
    lines.append("")
    lines.append("---")
    lines.append("## 🏷️ 本周高频关键词")
    all_text = " ".join(twitter + [p for posts in reddit.values() for p in posts] + [p.get("t","") for p in xq_posts])
    keywords_count = {}
    for kw in ["AI", "芯片", "半导体", "关税", "特朗普", "美联储", "通胀", "科技", 
               "China", "中国", "经济", "政策", "贸易", "战争", "和平"]:
        count = all_text.lower().count(kw.lower())
        if count >= 2:
            keywords_count[kw] = count
    top_kw = sorted(keywords_count.items(), key=lambda x: -x[1])[:10]
    for kw, cnt in top_kw:
        bar = "█" * min(cnt, 10)
        lines.append(f"- **{kw}**: {bar} ({cnt})")

    lines.append("")
    lines.append("---")
    lines.append(f"*由 Agent Reach (Twitter+Reddit+雪球) 自动生成 · {now}*")

    body = "\n".join(lines)
    # 企业微信 markdown 限制 4096，超了截断
    if len(body) > 4000:
        body = body[:3990] + "\n\n... (内容过长已截断)"
    return body


def push_webhook(body):
    """通过企业微信 Webhook 推送"""
    webhook = os.environ.get("WECHAT_WEBHOOK_URL", "")
    if not webhook:
        # try to read from hermes env
        hermes_env = os.path.expanduser("~/.hermes/env")
        if os.path.exists(hermes_env):
            for line in open(hermes_env):
                if line.startswith("WECHAT_WEBHOOK_URL="):
                    webhook = line.split("=", 1)[1].strip()
                    break
    if not webhook:
        print("ERROR: WECHAT_WEBHOOK_URL not set")
        return False

    payload = json.dumps({"msgtype": "markdown", "markdown": {"content": body}}, ensure_ascii=False)
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", webhook, "-H", "Content-Type: application/json", "-d", payload],
        capture_output=True, text=True, timeout=10
    )
    print(f"Webhook response: {r.stdout[:200]}")
    return r.returncode == 0


def main():
    print("📡 Fetching Twitter...")
    twitter = fetch_twitter_news(15)

    print("📡 Fetching Reddit...")
    reddit = fetch_reddit_topics()

    print("📡 Fetching Xueqiu...")
    xueqiu = fetch_xueqiu_digest()

    print("📝 Formatting markdown...")
    body = format_markdown(twitter, reddit, xueqiu)

    print(f"📤 Pushing to WeChat Work ({len(body)} chars)...")
    ok = push_webhook(body)
    print(f"Done: {'✅' if ok else '❌'}")

    # Also print to stdout for cron logs
    print("\n=== PREVIEW ===")
    print(body[:500])


if __name__ == "__main__":
    main()
