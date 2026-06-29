#!/usr/bin/env python3
"""
每周中外新闻数据拉取器 — 为 LLM 提供原始素材
数据源: Twitter/Reddit/雪球 → 结构化 JSON
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


def _load_auth_env():
    """从 venv activate 脚本加载 Twitter/Reddit 认证"""
    env = {}
    activate_file = os.path.join(AGENT_REACH_VENV, "bin", "activate")
    if os.path.exists(activate_file):
        with open(activate_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export ") and "=" in line:
                    line = line[7:]  # strip "export "
                    if "TWITTER_AUTH_TOKEN" in line or "TWITTER_CT0" in line:
                        key, val = line.split("=", 1)
                        val = val.strip("'\"")
                        env[key] = val
    return env


_AUTH_ENV = None

def _get_auth_env():
    global _AUTH_ENV
    if _AUTH_ENV is None:
        _AUTH_ENV = _load_auth_env()
    return _AUTH_ENV


def _run(cmd, timeout=25):
    env = os.environ.copy()
    env["PATH"] = f"{BIN}:{env.get('PATH', '')}"
    env.update(_get_auth_env())  # inject Twitter tokens
    try:
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=timeout, env=env)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def fetch_twitter_raw(n=20):
    """Twitter Feed — 完整文本，不过滤"""
    out = _run(f"twitter feed -n {n}", timeout=30)
    items = []
    if out:
        for line in out.split('\n'):
            line = line.strip()
            if line.startswith('text:') and len(line) > 20:
                text = line[5:].strip().replace('\n', ' ')[:300]
                # detect language
                has_cjk = bool(re.search(r'[\u4e00-\u9fff]', text))
                items.append({"text": text, "lang": "zh" if has_cjk else "en"})
    return items[:15]


def fetch_reddit_raw():
    """Reddit 多板块 — 完整标题"""
    subs = ["worldnews", "technology", "economics", "stocks", "wallstreetbets", "investing", "China"]
    results = {}
    for sub in subs:
        out = _run(f"rdt sub {sub} --limit 6", timeout=30)
        posts = []
        if out:
            for line in out.split('\n'):
                m = re.search(r'"title":\s*"([^"]+)"', line)
                if m:
                    title = m.group(1)
                    posts.append({"title": title, "lang": "en"})  # Reddit mostly English
        results[sub] = posts[:5]
    return results


def fetch_xueqiu_raw():
    """雪球热帖 + 热股"""
    script = (
        f'import sys, json\n'
        f'sys.path.insert(0, "{AGENT_REACH_VENV}/lib/python3.12/site-packages")\n'
        f'from agent_reach.channels.xueqiu import XueqiuChannel\n'
        f'ch = XueqiuChannel()\n'
        f'r = {{}}\n'
        f'try:\n'
        f'    posts = ch.get_hot_posts(limit=20)\n'
        f'    r["hot_posts"] = [{{"title": p.get("title","?")[:150], "replies": p.get("reply_count",0)}} for p in (posts or [])[:20]]\n'
        f'except Exception as e:\n'
        f'    r["hot_posts_err"] = str(e)[:100]\n'
        f'try:\n'
        f'    stocks = ch.get_hot_stocks(limit=12)\n'
        f'    r["hot_stocks"] = [{{"name": s.get("name","?"), "symbol": s.get("symbol","?"), "pct": s.get("percent","?"), "price": s.get("current","?")}} for s in (stocks or [])[:12]]\n'
        f'except Exception as e:\n'
        f'    r["hot_stocks_err"] = str(e)[:100]\n'
        f'print(json.dumps(r, ensure_ascii=False))\n'
    )
    out = _run(f'{PYTHON} -c \'{script}\'', timeout=30)
    try:
        return json.loads(out) if out else {}
    except Exception:
        return {"raw": str(out)[:500]}


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    output = {
        "meta": {
            "source": "agent_reach_weekly_fetcher",
            "generated_at": now,
            "week_range": f"{WEEK_AGO} ~ {now}",
            "instruction": (
                "你是一个资深财经编辑+投资分析师。请完成以下任务：\n"
                "1. 将所有英文内容翻译为中文（保留原标题的准确性）\n"
                "2. 按主题分类整理（时政/金融/科技/经济）\n"
                "3. 每个分类选择最值得关注的 Top 5-8 条\n"
                "4. 分 3-4 条消息推送企业微信（每条 < 4000 字符）：\n"
                "   - 消息1: 🌐 全球要闻 (Twitter/Reddit世界新闻)\n"
                "   - 消息2: 💰 金融市场 (Reddit stocks/investing + 雪球热股)\n"
                "   - 消息3: 📈 A股社区 + 科技动向\n"
                "   - 消息4: 🔮 行业前瞻与投资方向建议 (你的分析)\n"
                "5. 每条消息用 markdown 格式，通过 curl POST 到企业微信 webhook\n"
                "6. 最后一条消息必须包含：\n"
                "   - 📊 本周市场主线（1-2句话概括）\n"
                "   - 🔭 下周关注焦点（重要事件/数据/政策）\n"
                "   - 💡 投资方向建议（基于本周新闻的趋势判断，分板块）\n"
                "   - ⚠️ 风险提示\n"
                "使用 curl -s -X POST $WECHAT_WEBHOOK_URL -H 'Content-Type: application/json' -d '{\"msgtype\":\"markdown\",\"markdown\":{\"content\":\"...\"}}' 逐条发送"
            )
        },
        "data": {
            "twitter": fetch_twitter_raw(),
            "reddit": fetch_reddit_raw(),
            "xueqiu": fetch_xueqiu_raw(),
        }
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
