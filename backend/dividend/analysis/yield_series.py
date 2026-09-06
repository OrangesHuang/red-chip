"""逐日 TTM 股息率序列重构(纯函数)。

对每个交易日 t:
    dps_ttm(t) = 除净日落在 (t-365, t] 区间内全部现金股息之和
    yield(t)   = dps_ttm(t) / close(t) × 100

这样股息率历史曲线真实反映「当时的分红水平 ÷ 当时的价格」, 而不是用
当前 DPS 回填历史(会扭曲历史估值区间)。K 线须为前复权, 分红为除净口径。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def trailing_dps(
    dividends: list[dict],
    as_of: date | None = None,
    days: int = 365,
    exclude_special: bool = True,
) -> float:
    """截至 as_of(默认今天)的滚动 TTM 每股股息(港元)。

    只统计除净日(ex_date)在 (as_of-days, as_of] 内的现金分红;
    无除净日但有派息日的用派息日, 都没有的忽略。
    exclude_special: 剔除一次性特别股息(扭曲股息率锚点, 见 config)。
    """
    as_of = as_of or date.today()
    cutoff = as_of - timedelta(days=days)
    total = 0.0
    for r in dividends:
        if exclude_special and r.get("special"):
            continue
        anchor = _parse_date(r.get("ex_date")) or _parse_date(r.get("pay_date"))
        if anchor is None:
            continue
        if cutoff < anchor <= as_of:
            cash = r.get("cash_per_share")
            if cash:
                total += float(cash)
    return round(total, 6)


def build_daily_yield_series(kline: list[dict], dividends: list[dict], lookback: int | None = None) -> list[dict]:
    """由日 K 线与分红历史重构逐日股息率序列。

    返回 [{date, close, dps_ttm, div_yield}], 日期升序; div_yield 为 None 表示
    dps_ttm 缺失(如该日无有效分红记录)。lookback 限制返回最近 N 根。
    """
    if not kline:
        return []
    series: list[dict] = []
    for bar in kline:
        d = _parse_date(bar["date"])
        if d is None:
            continue
        dps = trailing_dps(dividends, as_of=d)
        close = bar["close"]
        yield_pct = round(dps / close * 100.0, 4) if dps > 0 and close > 0 else None
        series.append({"date": bar["date"], "close": close, "dps_ttm": dps, "div_yield": yield_pct})
    if lookback and lookback > 0:
        series = series[-lookback:]
    return series
