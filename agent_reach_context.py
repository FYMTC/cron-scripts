#!/usr/bin/env python3
"""
Agent Reach Context Fetcher — 为量化系统 cron 提供多渠道情绪数据
输出结构化 JSON 到 stdout

用法:
  source ~/.agent-reach-venv/bin/activate
  export TWITTER_AUTH_TOKEN='xxx'
  export TWITTER_CT0='yyy'
  python3 agent_reach_context.py morning   # 盘前模式
  python3 agent_reach_context.py night     # 夜报模式
"""
import json
import re
import subprocess
import sys
import os
from datetime import datetime

AGENT_REACH_VENV = os.path.expanduser("~/.agent-reach-venv")
BIN = f"{AGENT_REACH_VENV}/bin"
PYTHON = f"{BIN}/python3"


def _run(cmd, timeout=25):
    """Run command with agent-reach venv on PATH"""
    env = os.environ.copy()
    env["PATH"] = f"{BIN}:{env.get('PATH', '')}"
    try:
        r = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout, env=env
        )
        if r.returncode == 0:
            return r.stdout.strip()
        return f"EXIT:{r.returncode} {r.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR:{e}"


def fetch_twitter_feed(n=6):
    """Twitter 首页 Feed — 全球宏观/突发新闻"""
    out = _run(f"twitter feed -n {n}", timeout=30)
    items = []
    if out and not out.startswith("ERROR") and not out.startswith("EXIT") and not out.startswith("TIMEOUT"):
        for line in out.split('\n'):
            line = line.strip()
            if line.startswith('text:') and len(line) > 6:
                text = line[5:].strip().replace('\n', ' ')[:200]
                items.append(text)
    if not items:
        items.append(f"TWITTER_UNAVAILABLE: {out[:100]}")
    return items


def fetch_reddit_hot():
    """Reddit 投资板块热门 — rdt CLI 输出 YAML，从中提取 title"""
    results = {}
    for sub in ['stocks', 'wallstreetbets', 'investing']:
        out = _run(f"rdt sub {sub} --limit 4", timeout=30)
        titles = []
        if out and not out.startswith("ERROR") and not out.startswith("EXIT"):
            for line in out.split('\n'):
                # YAML format: "title": "Some Post Title"
                if '"title":' in line and len(line) > 20:
                    # Extract quoted title value
                    m = re.search(r'"title":\s*"([^"]+)"', line)
                    if m:
                        titles.append(m.group(1)[:150])
        results[sub] = titles[:4] if titles else [f"NO_TITLES: {out[:100]}"]
    return results


def fetch_xueqiu():
    """雪球 A 股社区 — 热股+热门帖"""
    script = (
        f'import sys, json\n'
        f'sys.path.insert(0, "{AGENT_REACH_VENV}/lib/python3.12/site-packages")\n'
        f'try:\n'
        f'    from agent_reach.channels.xueqiu import XueqiuChannel\n'
        f'    ch = XueqiuChannel()\n'
        f'    r = {{}}\n'
        f'    try:\n'
        f'        s = ch.get_hot_stocks(limit=8)\n'
        f'        r["hot_stocks"] = [{{"n": x.get("name","?"), "pct": x.get("percent","?"), "px": x.get("current","?")}} for x in (s or [])[:8]]\n'
        f'    except Exception as e:\n'
        f'        r["hot_stocks_err"] = str(e)[:100]\n'
        f'    try:\n'
        f'        p = ch.get_hot_posts(limit=6)\n'
        f'        r["hot_posts"] = [{{"t": x.get("title","?")[:80], "r": x.get("reply_count",0)}} for x in (p or [])[:6]]\n'
        f'    except Exception as e:\n'
        f'        r["hot_posts_err"] = str(e)[:100]\n'
        f'    print(json.dumps(r, ensure_ascii=False))\n'
        f'except Exception as e:\n'
        f'    print(json.dumps({{"error": str(e)[:200]}}, ensure_ascii=False))\n'
    )
    out = _run(f'{PYTHON} -c \'{script}\'', timeout=30)
    try:
        return json.loads(out) if out else {"error": "empty output"}
    except Exception:
        return {"raw": str(out)[:300]}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = {
        "source": "agent_reach_context",
        "generated_at": now,
        "mode": mode,
    }

    if mode in ("morning", "all"):
        output["twitter_feed"] = fetch_twitter_feed(6)
        output["reddit"] = fetch_reddit_hot()

    output["xueqiu"] = fetch_xueqiu()

    if mode in ("night", "all"):
        output["cross_market_note"] = (
            "对比雪球热股(A股社区) vs Reddit热帖(美股情绪)："
            "方向一致→全球共振风险/机会；方向背离→结构性分化，存在套利空间"
        )

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
