"""ReAct 分析 Agent: DeepSeek 模型 + 工具调用循环。

循环协议: 模型每一步输出 JSON, 两种形态之一:
    {"tool": "工具名", "args": {...}}   → 执行工具, 结果回填后继续
    {"final": "最终报告(markdown)"}     → 结束循环

工具注册表 _TOOLS: 新增工具只需加一个函数 + 一行注册。
"""

from __future__ import annotations

import json
import re
import subprocess

from base.config import (
    DEFAULT_STOCK_CODE,
    LLM_BASH_MAX_OUTPUT,
    LLM_BASH_TIMEOUT,
    LLM_MAX_STEPS,
)
from base.llm.client import chat_completion_rich

# ─── 工具实现 ──────────────────────────────────────────────────────


def _tool_get_stock_data(args: dict) -> str:
    """个股完整分析上下文(因子/区间/赔率/分红/K线统计/资讯)。"""
    from dividend.service import build_llm_context

    code = str(args.get("code") or args.get("symbol") or DEFAULT_STOCK_CODE)
    ctx = build_llm_context(code)
    return json.dumps(ctx, ensure_ascii=False)


def _tool_get_stock_news(args: dict) -> str:
    """个股最近资讯(标题/时间/来源)。"""
    from base.fetch.news import fetch_stock_news

    code = str(args.get("code") or args.get("symbol") or DEFAULT_STOCK_CODE)
    limit = int(args.get("limit") or 10)
    news = fetch_stock_news(code, limit=limit)
    return json.dumps(
        [{"title": n["title"], "time": n["time"], "source": n["source"]} for n in news],
        ensure_ascii=False,
    )


def _tool_get_pool(args: dict) -> str:
    """全股票池因子快照(横向对照其他高股息标的)。"""
    from dividend.service import build_pool

    pool = build_pool()
    summary = [
        {
            "code": s["code"],
            "name": s["name"],
            "market": s["market"],
            "div_yield": s["div_yield"],
            "score": s["score"],
            "grade": s["grade"],
            "zone": s["zone"],
            "odds": s["odds"],
        }
        for s in pool
    ]
    return json.dumps(summary, ensure_ascii=False)


def _tool_bash(args: dict) -> str:
    """执行 bash 命令(本地自用工具, 30s 超时, 输出截断)。"""
    cmd = str(args.get("command") or "").strip()
    if not cmd:
        return "空命令"
    if len(cmd) > 2000:
        return "命令过长(≤2000字符)"
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=LLM_BASH_TIMEOUT,
        )
        out = (proc.stdout or "")[-LLM_BASH_MAX_OUTPUT:]
        err = (proc.stderr or "")[-1000:]
        return f"exit={proc.returncode}\nstdout:\n{out}\nstderr:\n{err}".strip()
    except subprocess.TimeoutExpired:
        return f"命令超时(>{LLM_BASH_TIMEOUT}s)"
    except Exception as e:  # noqa: BLE001
        return f"命令执行失败: {e}"


_TOOLS: dict[str, dict] = {
    "get_stock_data": {
        "desc": "获取单只股票的分析数据。参数: {\"code\": \"股票代码\"}",
        "fn": _tool_get_stock_data,
    },
    "get_stock_news": {
        "desc": "获取单只股票的最近资讯。参数: {\"code\": \"股票代码\", \"limit\": 数量(默认10)}",
        "fn": _tool_get_stock_news,
    },
    "get_pool": {
        "desc": "获取全股票池的因子快照摘要(用于横向对比)。参数: {}",
        "fn": _tool_get_pool,
    },
    "bash": {
        "desc": "执行 bash 命令做补充计算(如 python 算数/爬虫), 30s 超时。参数: {\"command\": \"命令\"}",
        "fn": _tool_bash,
    },
}

SYSTEM_PROMPT = """你是「红筹高股息」股票分析助手, 专注 A 股/港股高股息个股的深度研究。
你可以调用以下工具获取数据(每次只调用一个):

可用工具:
1. get_stock_data — 获取单只股票的分析数据(因子分/股息率TTM/价格区间/赔率/分红历史/K线统计/股息率分位)。参数: {"code": "00941"}
2. get_stock_news — 获取单只股票的最近资讯。参数: {"code": "00941"}
3. get_pool — 获取全股票池因子快照摘要(横向对照)
4. bash — 执行 bash 命令做补充计算(谨慎使用, 只读操作优先)

工作流程(重要):
1. 先调用 get_stock_data 获取标的(如 00941)的数据;
2. 再调用 get_stock_news 查看最新资讯, 理解股价近期为何涨跌;
3. 需要横向对比时调用 get_pool; 数据不够时可用 bash 补充计算;
4. 综合分析后给出最终报告(不再调用工具)。

分析框架(每个方面都要覆盖):
- 股息质量: TTM股息率、分红连续性与成长性、特别股息剔除后的可持续性、派息率/负债率是否异常
- 估值区间: 当前股息率处于近5年分位的位置, 低估/高估判定, 锚定价格(中枢/乐观/悲观)
- 赔率评估: 上行空间/下行空间, 赔率是否吸引人; 注意"高股息可能伴随价值陷阱风险"
- 风险提示: 分红削减风险、盈利下滑、A/H溢价、行业与政策风险; 区分"错杀"与"基本面恶化"
- 结论: 给出明确观点(值得关注/观望/回避)与关键观察点

多轮会话规则(重要, 强制遵守):
- 每一轮用户提问都是新的分析指令, 必须完整响应, 不得敷衍或只复述前一轮结论;
- 用户提到的其他标的(如"对比中国神华/601088"、"与长江电力比"), 必须先调用
  get_stock_data 或 get_pool 获取其数据, 再进行比较分析;
- 前一轮的工具返回不会自动保留, 需要数据就重新调用工具获取, 不要凭记忆编造。

数据诚实性(强制遵守):
- 工具返回的数据里没有的字段(如派息率、负债率、净利润、现金流等财务指标尚未接入数据源),
  一律不得编造数字; 相关分析应明确写"该数据未接入, 待补充", 或基于已有分红/股息数据推理并标注"推测"。
- 引用任何数字必须来自工具返回内容, 引用新闻时注明新闻标题/时间。

输出格式(严格遵守):
- 需要工具时输出 JSON: {"tool": "工具名", "args": {...}}
- 最终报告时输出 JSON: {"final": "markdown报告"}

报告用中文 markdown, 结构: ## 结论摘要 → ## 股息质量 → ## 估值与赔率 → ## 风险提示 → ## 操作建议。
报告末尾附一行: "> 本报告由 AI 基于历史数据自动生成, 不构成投资建议。" """


def parse_llm_json(content: str) -> dict:
    """从模型输出中提取 JSON(容忍 markdown 代码围栏与前后杂文)。失败返回 {"final": 原文}。"""
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {"final": content or "(空响应)"}


def run_analysis(
    code: str,
    on_step=None,
    history: list[dict] | None = None,
    usage_acc: dict | None = None,
    user_prompt: str | None = None,
) -> str:
    """执行 ReAct 分析循环, 返回最终 markdown 报告。

    多轮会话: history 为前序轮次的 [(user 提问, assistant 报告)] 消息(只保留
    问答, 不含工具内部细节 — 保持上下文前缀紧凑, 最大化 DeepSeek 磁盘缓存命中)。
    user_prompt: 本轮用户的实际提问(多轮会话必须传入, 否则模型只会回答通用分析)。
    usage_acc: 传入 dict 则累计本轮的 token 用量(含缓存命中/未命中)。

    on_step(kind, message, detail=None, update=False):
        kind: round(模型决策, detail=原始JSON) / tool(工具执行, detail=返回摘要) /
              usage(本轮缓存统计) / done / error
    """
    from base.pool import get_stock

    info = get_stock(code) or {"name": code}
    target = f"{code} {info.get('name', '')}(市场 {info.get('market', '')})"
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    raw_prompt = (user_prompt or "").strip()
    if raw_prompt:
        # 多轮追问: 必须显式标注分析标的, 否则模型可能分析其他股票(或工具漏传代码)
        prompt = (
            f"【本次分析标的: {target}】请始终围绕该标的回答, 不要分析或切换到其他股票。\n"
            f"用户问题: {raw_prompt}"
        )
    else:
        prompt = f"请深度分析股票 {target}。先获取数据与资讯, 再综合给出报告。"
    messages.append({"role": "user", "content": prompt})

    def step(kind: str, msg: str, detail: str | None = None, update: bool = False) -> None:
        if on_step:
            on_step(kind, msg, detail, update)

    def record_usage(usage: dict) -> None:
        if usage_acc is not None:
            for k in ("prompt_tokens", "completion_tokens", "cache_hit_tokens", "cache_miss_tokens"):
                usage_acc[k] = usage_acc.get(k, 0) + usage.get(k, 0)
            usage_acc["rounds"] = usage_acc.get("rounds", 0) + 1
        step(
            "usage",
            f"本轮输入 {usage.get('prompt_tokens', 0)} tokens"
            f"(缓存命中 {usage.get('cache_hit_tokens', 0)} / 未命中 {usage.get('cache_miss_tokens', 0)}),"
            f" 输出 {usage.get('completion_tokens', 0)}",
        )

    for i in range(LLM_MAX_STEPS):
        step("round", f"第 {i + 1}/{LLM_MAX_STEPS} 轮: 正在请求模型…")
        content, usage = chat_completion_rich(messages)
        record_usage(usage)

        # 空响应/解析失败兜底: 明确提示重试, 不静默带病继续
        if not content or not content.strip():
            step("round", f"第 {i + 1}/{LLM_MAX_STEPS} 轮: 模型返回空响应, 已要求重试")
            messages.append(
                {"role": "user", "content": "你的上轮输出为空, 请重新输出 JSON(工具调用或 {\"final\": 报告})。"}
            )
            continue

        parsed = parse_llm_json(content)
        final = parsed.get("final")
        if isinstance(final, str) and final.strip():
            step("round", f"第 {i + 1}/{LLM_MAX_STEPS} 轮: 模型给出结论", detail=content[:600])
            step("done", "分析完成")
            return final.strip()

        tool = parsed.get("tool")
        if not isinstance(tool, str) or not tool:
            step("round", f"第 {i + 1}/{LLM_MAX_STEPS} 轮: 输出无法解析为工具调用, 已纠正", detail=content[:600])
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {"role": "user", "content": "请严格按照格式输出 JSON: {\"tool\": \"工具名\", \"args\": {...}} 或 {\"final\": \"报告\"}。"}
            )
            continue
        args = parsed.get("args") or {}
        if tool not in _TOOLS:
            step("round", f"第 {i + 1}/{LLM_MAX_STEPS} 轮: 模型请求了未知工具 {tool!r}, 已纠正", detail=content[:600])
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {"role": "user", "content": f"工具 {tool} 不存在, 可用工具: {', '.join(_TOOLS)}。请重新输出 JSON。"}
            )
            continue

        # 标的代码注入(防错标的): 个股类工具漏传 code 时, 强制用本次分析目标,
        # 绝不静默回退默认股票(曾导致腾讯控股会话弹出中国移动数据的 bug)
        if tool in ("get_stock_data", "get_stock_news") and not args.get("code") and not args.get("symbol"):
            args = dict(args)
            args["code"] = code
            step("tool", f"模型未指定代码, 已自动注入分析标的 {code}", detail=None)

        step("round", f"第 {i + 1}/{LLM_MAX_STEPS} 轮: 模型决定调用工具 {tool}", detail=content[:600])
        step("tool", f"正在执行工具 {tool} {json.dumps(args, ensure_ascii=False)[:120]}…")
        try:
            result = _TOOLS[tool]["fn"](args)
        except Exception as e:  # noqa: BLE001
            result = f"工具执行异常: {e}"
        step("tool", f"工具 {tool} 返回", detail=str(result)[:400], update=True)
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": f"工具 {tool} 返回:\n{str(result)[:4000]}"})

    # 超步数兜底: 强制出最终报告
    step("round", "已达最大轮数, 要求模型直接给出结论")
    messages.append(
        {"role": "user", "content": "已达最大工具轮数, 请基于已有信息直接输出最终报告(JSON {\"final\": ...})。"}
    )
    content, usage = chat_completion_rich(messages)
    record_usage(usage)
    parsed = parse_llm_json(content)
    final = parsed.get("final")
    if not (isinstance(final, str) and final.strip()):
        from base.llm.client import LLMError

        raise LLMError("模型多次未能输出有效报告(响应为空或格式错误), 请重试")
    step("round", "模型输出最终结论", detail=content[:600])
    step("done", "分析完成")
    return final.strip()
