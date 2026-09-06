"""通用数值纯函数: 分位数/分位排名/价格位置/均线。"""

from __future__ import annotations

import bisect
from statistics import fmean


def quantiles(values: list[float], qs: list[float] | None = None) -> dict[str, float]:
    """线性插值分位数。qs 默认 [10, 25, 50, 75, 90, 95]。空输入返回空 dict。"""
    if qs is None:
        qs = [10.0, 25.0, 50.0, 75.0, 90.0, 95.0]
    if not values:
        return {}
    ordered = sorted(values)
    n = len(ordered)
    result: dict[str, float] = {}
    for q in qs:
        if q <= 0.0:
            result[str(q)] = ordered[0]
            continue
        if q >= 100.0:
            result[str(q)] = ordered[-1]
            continue
        pos = (n - 1) * q / 100.0
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        result[str(q)] = ordered[lo] + (ordered[hi] - ordered[lo]) * frac
    return result


def percentile_rank(values: list[float], x: float) -> float | None:
    """x 在 values 中的百分位排名(0~100, 线性)。x 低于全部 → 0, 高于全部 → 100。"""
    if not values:
        return None
    ordered = sorted(values)
    if x <= ordered[0]:
        return 0.0
    if x >= ordered[-1]:
        return 100.0
    idx = bisect.bisect_left(ordered, x)
    return round(idx / (len(ordered) - 1) * 100.0, 1)


def price_position(kline: list[dict], window: int = 60) -> float | None:
    """近 window 根 K 线内收盘价位置: (close - low) / (high - low) × 100。"""
    if not kline:
        return None
    recent = kline[-window:]
    highs = [r["high"] for r in recent]
    lows = [r["low"] for r in recent]
    close = recent[-1]["close"]
    span = max(highs) - min(lows)
    if span <= 0:
        return 100.0 if close >= max(highs) else 0.0
    return round((close - min(lows)) / span * 100.0, 1)


def sma(values: list[float], window: int) -> list[float | None]:
    """简单移动平均; 前 window-1 个位置为 None。"""
    if window <= 0:
        return [None] * len(values)
    result: list[float | None] = []
    acc = 0.0
    for i, v in enumerate(values):
        acc += v
        if i >= window:
            acc -= values[i - window]
        if i >= window - 1:
            result.append(round(acc / window, 4))
        else:
            result.append(None)
    return result


def annualized_volatility(closes: list[float], window: int = 120) -> float | None:
    """年化波动率 %: 近 window 个收盘价的日收益率标准差 × √252 × 100。"""
    if len(closes) < window + 1:
        return None
    recent = closes[-(window + 1):]
    returns = []
    for i in range(1, len(recent)):
        prev = recent[i - 1]
        if prev and prev > 0:
            returns.append(recent[i] / prev - 1.0)
    if len(returns) < 2:
        return None
    mean = fmean(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return round(var**0.5 * (252**0.5) * 100.0, 2)
