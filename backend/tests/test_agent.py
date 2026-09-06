"""ReAct Agent 测试: mock LLM 验证循环/解析/兜底逻辑(不触网)。"""

from __future__ import annotations

from base.llm import agent


def test_parse_llm_json_variants():
    # 纯 JSON
    assert agent.parse_llm_json('{"tool": "bash", "args": {"command": "ls"}}') == {
        "tool": "bash",
        "args": {"command": "ls"},
    }
    # markdown 代码围栏
    assert agent.parse_llm_json('```json\n{"final": "报告"}\n```') == {"final": "报告"}
    # 前后杂文 + 花括号提取
    assert agent.parse_llm_json('好的, 我来分析:\n{"tool": "get_stock_data", "args": {"code": "00941"}}\n请稍候') == {
        "tool": "get_stock_data",
        "args": {"code": "00941"},
    }
    # 无法解析 → 兜底为 final
    parsed = agent.parse_llm_json("完全不是 JSON 的文本")
    assert parsed["final"] == "完全不是 JSON 的文本"


def test_run_analysis_loop(monkeypatch):
    """工具调用 → 结果回填 → 最终报告; 工具被正确执行且步骤有记录。"""
    calls: list[str] = []

    def fake_chat(messages, **kwargs):
        # 第一次: 要工具; 第二次: 要资讯; 第三次: 给最终报告
        tool_calls = [t for t in messages if t["role"] == "assistant"]
        n = len(tool_calls)
        if n == 0:
            return '{"tool": "get_stock_data", "args": {"code": "00941"}}', {"prompt_tokens": 100, "completion_tokens": 20, "cache_hit_tokens": 80, "cache_miss_tokens": 20}
        if n == 1:
            return '{"tool": "get_stock_news", "args": {"code": "00941"}}', {"prompt_tokens": 200, "completion_tokens": 20, "cache_hit_tokens": 190, "cache_miss_tokens": 10}
        return '{"final": "## 结论\\n分析完成"}', {"prompt_tokens": 300, "completion_tokens": 50, "cache_hit_tokens": 300, "cache_miss_tokens": 0}

    def fake_tool_data(args):
        calls.append("data")
        return '{"stock": {"code": "00941"}}'

    def fake_tool_news(args):
        calls.append("news")
        return '[]'

    monkeypatch.setattr(agent, "chat_completion_rich", fake_chat)
    monkeypatch.setitem(agent._TOOLS["get_stock_data"], "fn", fake_tool_data)
    monkeypatch.setitem(agent._TOOLS["get_stock_news"], "fn", fake_tool_news)

    steps: list[tuple] = []
    usage: dict = {}
    report = agent.run_analysis("00941", on_step=lambda k, m, d=None, u=False: steps.append((k, m, d, u)), usage_acc=usage)

    assert report == "## 结论\n分析完成"
    assert calls == ["data", "news"]
    kinds = [k for k, _, _, _ in steps]
    assert "tool" in kinds and "done" in kinds
    # usage 累计: 三次调用
    assert usage["prompt_tokens"] == 600
    assert usage["cache_hit_tokens"] == 570
    assert usage["rounds"] == 3
    # 缓存统计步骤存在
    assert "usage" in kinds
    # 轮次步骤应带模型决策 detail; 工具步骤 detail 为返回摘要
    round_details = [d for k, _, d, _ in steps if k == "round" and d]
    tool_details = [d for k, _, d, _ in steps if k == "tool" and d]
    assert round_details and "get_stock_data" in round_details[0]
    assert tool_details and tool_details[0] == '{"stock": {"code": "00941"}}'
    # 工具占位步骤使用 update=True 回填
    updates = [u for _, _, _, u in steps]
    assert any(updates)


def test_run_analysis_unknown_tool_recovers(monkeypatch):
    """模型请求不存在的工具 → 提示纠正后继续, 不死循环。"""

    def fake_chat(messages, **kwargs):
        tool_calls = [t for t in messages if t["role"] == "assistant"]
        n = len(tool_calls)
        if n == 0:
            return '{"tool": "not_exist", "args": {}}', {}
        if n == 1:
            return '{"final": "OK"}', {}
        return '{"final": "OK"}', {}

    monkeypatch.setattr(agent, "chat_completion_rich", fake_chat)
    report = agent.run_analysis("00941")
    assert report == "OK"


def test_run_analysis_max_steps_force_final(monkeypatch):
    """模型一直要工具 → 超步数后强制要求最终报告。"""

    def fake_chat(messages, **kwargs):
        tool_calls = [t for t in messages if t["role"] == "assistant"]
        if len(tool_calls) < agent.LLM_MAX_STEPS:
            return '{"tool": "get_pool", "args": {}}', {}
        return '{"final": "兜底报告"}', {}

    def fake_pool(args):
        return "[]"

    monkeypatch.setattr(agent, "chat_completion_rich", fake_chat)
    monkeypatch.setitem(agent._TOOLS["get_pool"], "fn", fake_pool)
    report = agent.run_analysis("00941")
    assert report == "兜底报告"


def test_run_analysis_with_history(monkeypatch):
    """多轮会话: 历史(用户提问+AI报告)进入 messages, 且保持顺序。"""
    captured: dict = {}

    def fake_chat(messages, **kwargs):
        captured["messages"] = list(messages)
        return '{"final": "续答"}', {"cache_hit_tokens": 999, "prompt_tokens": 100, "completion_tokens": 10}

    monkeypatch.setattr(agent, "chat_completion_rich", fake_chat)
    history = [
        {"role": "user", "content": "第一问"},
        {"role": "assistant", "content": "第一答"},
    ]
    report = agent.run_analysis("00941", history=history)
    assert report == "续答"
    roles = [m["role"] for m in captured["messages"]]
    contents = [m["content"] for m in captured["messages"]]
    assert roles == ["system", "user", "assistant", "user"]
    assert contents[:3] == [agent.SYSTEM_PROMPT, "第一问", "第一答"]


def test_run_analysis_uses_user_prompt(monkeypatch):
    """多轮会话: 用户真实提问必须进入消息(此前被通用提示词替代的 bug 回归测试)。"""
    captured: dict = {}

    def fake_chat(messages, **kwargs):
        captured["messages"] = list(messages)
        return '{"final": "回答"}', {}

    monkeypatch.setattr(agent, "chat_completion_rich", fake_chat)
    agent.run_analysis("00941", history=[], user_prompt="8月25日那天为什么会跌呢?")
    assert captured["messages"][-1] == {"role": "user", "content": "8月25日那天为什么会跌呢?"}


def test_run_analysis_generic_prompt_when_no_user_prompt(monkeypatch):
    """无 user_prompt 时(一次性分析接口)回退到通用提示词。"""
    captured: dict = {}

    def fake_chat(messages, **kwargs):
        captured["messages"] = list(messages)
        return '{"final": "回答"}', {}

    monkeypatch.setattr(agent, "chat_completion_rich", fake_chat)
    agent.run_analysis("00941")
    last = captured["messages"][-1]["content"]
    assert "请深度分析股票 00941" in last
