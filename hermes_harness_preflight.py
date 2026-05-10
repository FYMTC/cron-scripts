#!/config/quant_env/bin/python3
"""
hermes_harness_preflight.py — Harness通用前置脚本
=================================================
在每次cron执行前运行，输出结构化约束上下文注入cron prompt。

输出：
  === HARNESS PREFLIGHT ===
  (系统状态摘要 + 不变式声明 + 输出验证要求)
  === END HARNESS ===

用法：挂载到cron的script字段
"""

import subprocess, json, os, sys
from datetime import datetime

SCRIPTS_DIR = "/config/quant_scripts"
PYTHON = "/config/quant_env/bin/python3"

def run_claim_check():
    """运行全量组件审计"""
    try:
        r = subprocess.run(
            [PYTHON, os.path.join(SCRIPTS_DIR, "system_claim_verify.py"), "--check-all"],
            capture_output=True, text=True, timeout=30
        )
        return r.stdout.strip()
    except Exception as e:
        return f"[HARNES ERROR] claim check failed: {e}"

def main():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    claim_out = run_claim_check()
    
    output = f"""
═══════════════════════════════════════════════
 HARNESS PREFLIGHT — {now}
═══════════════════════════════════════════════

[系统状态]
{claim_out}

═══════════════════════════════════════════════
 INVARIANT ASSERTIONS (不得违反)
═══════════════════════════════════════════════

I1: 组件状态声明必须先查manifest
    任何关于"X组件是否在生产运行"的断言，必须先读取
    /config/quant_scripts/system_manifest.json 中该组件的 status 字段。
    禁止凭记忆回答系统集成状态。

I2: 交易建议必须走完四步门禁
    BUY/SELL/加仓/减仓/做T/低吸建议 → 完整 TradingAgents(≥3分析师)
    → score→mapping → T+1合规 → risk_check。
    未走完全流程的交易建议视为无效。

I3: 任何"已集成"必须有证据链
    声称某组件已集成到生产 = 必须有该组件的 manifest.status=active +
    近期的 actual_last_run 记录。否则必须标注 status 的实际值。

I4: 用户最后一条指令必须被显式回应
    用户的最后要求不得被忽略。回答中必须包含做了的证据或明确不做的理由。

I5: 事实性声明必须可验证
    任何代码/文件/脚本有关的断言，必须先通过实际读取文件或运行命令验证。
    禁止用"应该存在/我记得/通常是这样"代替验证。

═══════════════════════════════════════════════
 OUTPUT VERIFICATION (输出验证)
═══════════════════════════════════════════════

在发送最终输出前，必须完成以下4项自检：

□ CHECK 1 — 事实核查：本报告中所有关于"什么在运行/什么已集成"的声明，
  是否已通过 manifest 或实际运行验证？不是凭记忆？
  [如果违规 → 标记 ❌FACT 并修正]

□ CHECK 2 — 流程合规：如果本报告包含任何交易建议(BUY/SELL/调仓)，
  是否已完整走四步门禁并启动 TradingAgents？
  [如果违规 → 标记 ❌GATE 并修正]

□ CHECK 3 — 约束全量：本报告是否跳过了或"忘记"了用户的明确指令？
  是否有被忽略的要求？
  [如果违规 → 标记 ❌SKIP 并修正]

□ CHECK 4 — 偷懒检测：本报告是否用"已集成/已就绪"等词替代了实际执行？
  是否有用说代替做的嫌疑？
  [如果违规 → 标记 ❌LAZY 并修正]

如果任何检查项❌，必须先纠正再输出。

═══════════════════════════════════════════════
"""
    print(output)

if __name__ == "__main__":
    main()
