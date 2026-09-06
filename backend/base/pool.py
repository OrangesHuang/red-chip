"""股票池访问层: 内置池(config.STOCKS) + 用户自定义池(DB custom_stocks) 合并。

所有代码统一从这里取股票池, 不要直接读 config.STOCKS:
    get_all_stocks() / get_stock(code) / is_custom(code)
页面「添加股票」经 add_stock() 校验入池; 内置股票不可删除, 自定义可删。
"""

from __future__ import annotations

import re

from base.config import STOCKS
from base.store.pool_repo import add_custom_stock as _db_add
from base.store.pool_repo import get_custom_stocks as _db_list
from base.store.pool_repo import remove_custom_stock as _db_remove


def get_all_stocks() -> dict[str, dict]:
    """有效股票池 = 内置 + 自定义(自定义覆盖同代码的内置条目, 理论不会发生)。"""
    merged = dict(STOCKS)
    for row in _db_list():
        merged[row["code"]] = {
            "name": row["name"],
            "industry": row["industry"] or "自定义",
            "market": row["market"],
            "custom": True,
        }
    return merged


def get_stock(code: str) -> dict | None:
    """按代码取单只(内置或自定义), 不存在返回 None。"""
    info = STOCKS.get(code)
    if info:
        return dict(info)
    for row in _db_list():
        if row["code"] == code:
            return {
                "name": row["name"],
                "industry": row["industry"] or "自定义",
                "market": row["market"],
                "custom": True,
            }
    return None


def is_custom(code: str) -> bool:
    return code not in STOCKS and get_stock(code) is not None


def list_custom() -> list[dict]:
    return _db_list()


def detect_market(code: str) -> str | None:
    """按代码格式推断市场: 5位→hk; 6位 6/9开头→sh, 0/2/3开头→sz; 其余(如北交所)→None。"""
    if re.fullmatch(r"\d{5}", code):
        return "hk"
    if re.fullmatch(r"\d{6}", code):
        if code[0] in ("6", "9"):
            return "sh"
        if code[0] in ("0", "2", "3"):
            return "sz"
    return None


def add_stock(code: str, name: str | None = None, market: str | None = None, industry: str | None = None) -> tuple[bool, str]:
    """添加股票到池子。返回 (是否成功, 信息/错误)。

    校验: 代码格式(5/6位数字)、市场可推断、未与内置池/自定义池重复。
    """
    code = (code or "").strip()
    if not re.fullmatch(r"\d{5,6}", code):
        return False, "代码格式不正确: 应为 5 位港股或 6 位 A 股代码"

    if market is None or market not in ("hk", "sh", "sz"):
        market = detect_market(code)
        if market is None:
            return False, f"无法推断市场(代码 {code}), 请明确选择 hk/sh/sz"

    if get_stock(code) is not None:
        return False, f"{code} 已在股票池中"

    display_name = (name or "").strip() or code
    _db_add(code, display_name, market, industry or "自定义")
    return True, f"已添加 {display_name}({code}), 正在拉取数据…"


def remove_stock(code: str) -> tuple[bool, str]:
    """移除自定义股票(内置股票不可删), 并清理其数据。"""
    if code in STOCKS:
        return False, f"{code} 为内置股票, 不可删除(可编辑 config.STOCKS)"
    if not _db_remove(code):
        return False, f"{code} 不在自定义池中"
    return True, f"已移除 {code}"
