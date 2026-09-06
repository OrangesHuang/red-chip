"""交易日历(港股) — 占位实现。

港股交易日历暂未接入数据源(v1 用自然日近似: K 线区间拉取按自然日分块,
不依赖交易日历)。后续可接入港交所/港股通日历。接口保持与上层约定一致:
返回按日期升序的交易日列表, 失败返回空列表。
"""

from __future__ import annotations


def fetch_trade_days(start_date: str | None = None, end_date: str | None = None) -> list[str]:
    """拉取 [start_date, end_date] 区间内的港股交易日。TODO: 接入真实日历源。"""
    return []
