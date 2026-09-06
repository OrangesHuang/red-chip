"""股息率锚定的价格区间判断(纯函数)。

核心思想: 高股息股用「股息率」定价 —— 股息率越高代表价格越便宜。
以近 5 年逐日股息率序列的分位为基准:
    yield ≥ P75        → 低估区(便宜, 值得关注)
    yield ≤ P25        → 高估区(贵, 谨慎)
    其余               → 合理区
    yield ≥ P90 / ≤ P10 → 深度低估 / 深度高估(极端)

同时给出锚定价格: 年度每股股息 ÷ 目标股息率 = 对应价格。
"""

from __future__ import annotations

from base.analysis.position import quantiles
from base.config import (
    ODDS_Q_CENTRAL,
    ODDS_Q_OPTIMISTIC,
    ODDS_Q_PESSIMISTIC,
    ZONE_Q_DEEP_HIGH,
    ZONE_Q_DEEP_LOW,
    ZONE_Q_HIGH,
    ZONE_Q_LOW,
)


def yield_quantiles(yield_series: list[dict]) -> dict[str, float]:
    """逐日股息率序列 → 分位数 dict(键为字符串分位, 如 '25.0')。"""
    values = [p["div_yield"] for p in yield_series if p.get("div_yield") is not None]
    return quantiles(values)


def price_zone(current_yield: float | None, qs: dict[str, float]) -> str:
    """区间判定。current_yield 缺失 → 合理(未知)。"""
    if current_yield is None or not qs:
        return "合理"
    if current_yield >= qs.get(str(ZONE_Q_DEEP_LOW), float("inf")):
        return "深度低估"
    if current_yield >= qs.get(str(ZONE_Q_HIGH), float("inf")):
        return "低估"
    if current_yield <= qs.get(str(ZONE_Q_DEEP_HIGH), 0.0):
        return "深度高估"
    if current_yield <= qs.get(str(ZONE_Q_LOW), 0.0):
        return "高估"
    return "合理"


def anchor_prices(
    annual_dps: float, yield_series: list[dict], current_yield: float | None = None
) -> dict:
    """按股息率分位给出锚定价格。

    返回 {zone, qs, anchors:{low(低估阈值价), central(中枢价), high(高估阈值价),
    optimistic(乐观价), pessimistic(悲观价)}, current_yield}。
    价格 = annual_dps / (分位股息率/100); annual_dps ≤ 0 → 全部 None。
    """
    qs = yield_quantiles(yield_series)
    result: dict = {
        "zone": price_zone(current_yield, qs),
        "qs": {k: round(v, 4) for k, v in qs.items()},
        "anchors": {
            "low": None,
            "central": None,
            "high": None,
            "optimistic": None,
            "pessimistic": None,
        },
        "current_yield": round(current_yield, 4) if current_yield is not None else None,
    }
    if annual_dps <= 0:
        return result

    def _price(q: float) -> float | None:
        y = qs.get(str(q))
        if not y or y <= 0:
            return None
        return round(annual_dps / (y / 100.0), 4)

    result["anchors"] = {
        "low": _price(ZONE_Q_HIGH),  # 股息率到 P75(便宜端) → 价格低位阈值
        "central": _price(ODDS_Q_CENTRAL),  # 股息率到 P50(中枢) → 中枢价
        "high": _price(ZONE_Q_LOW),  # 股息率到 P25(贵端) → 价格高位阈值
        "optimistic": _price(ODDS_Q_OPTIMISTIC),  # 股息率到 P25 → 乐观价
        "pessimistic": _price(ODDS_Q_PESSIMISTIC),  # 股息率到 P95 → 悲观价
    }
    return result
