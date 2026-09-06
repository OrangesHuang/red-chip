"""DeepSeek(OpenAI 兼容) Chat Completions 客户端。

API Key / 模型 / 端点从 settings 表读取(页面可配置), 未配置时抛 LLMError。
支持 json_object 输出模式(工具调用解析更可靠)。
"""

from __future__ import annotations

import json
import urllib.request

from base.config import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)
from base.store.settings_repo import get_setting


class LLMError(Exception):
    """LLM 调用错误(未配置/网络/API 报错)。"""


def _resolve(api_key: str | None, model: str | None, base_url: str | None) -> tuple[str, str, str]:
    key = (api_key or "").strip() or (get_setting("llm_api_key") or "").strip()
    if not key:
        raise LLMError("未配置 DeepSeek API Key, 请到「数据管理 → AI 分析设置」填写")
    model = (model or "").strip() or (get_setting("llm_model") or "").strip() or DEFAULT_LLM_MODEL
    base = (base_url or "").strip() or (get_setting("llm_base_url") or "").strip() or DEFAULT_LLM_BASE_URL
    return key, model, base.rstrip("/")


def chat_completion(
    messages: list[dict],
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    json_mode: bool = True,
    temperature: float = LLM_TEMPERATURE,
    max_tokens: int = LLM_MAX_TOKENS,
) -> str:
    """单次补全, 返回 assistant 文本。json_mode=True 时要求模型输出合法 JSON。"""
    content, _ = chat_completion_rich(
        messages,
        api_key=api_key,
        model=model,
        base_url=base_url,
        json_mode=json_mode,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return content


def chat_completion_rich(
    messages: list[dict],
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    json_mode: bool = True,
    temperature: float = LLM_TEMPERATURE,
    max_tokens: int = LLM_MAX_TOKENS,
) -> tuple[str, dict]:
    """单次补全, 返回 (assistant 文本, usage 统计)。

    usage 含 DeepSeek 上下文磁盘缓存计数:
        prompt_tokens / completion_tokens / cache_hit_tokens / cache_miss_tokens
    (缓存为 DeepSeek 自动启用, 命中时输入费用约 1/10; 多轮会话复用前缀即可命中)。
    """
    key, model, base = _resolve(api_key, model, base_url)
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    # deepseek-reasoner 不支持 response_format, 自动降级为普通模式
    if json_mode and "reasoner" not in model:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"DeepSeek API 调用失败: {e}") from e

    try:
        content = str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as e:
        detail = data.get("error") or data
        raise LLMError(f"DeepSeek API 响应异常: {detail}") from e

    usage_raw = data.get("usage") or {}
    usage = {
        "prompt_tokens": usage_raw.get("prompt_tokens") or 0,
        "completion_tokens": usage_raw.get("completion_tokens") or 0,
        "cache_hit_tokens": usage_raw.get("prompt_cache_hit_tokens") or 0,
        "cache_miss_tokens": usage_raw.get("prompt_cache_miss_tokens") or 0,
    }
    return content, usage
