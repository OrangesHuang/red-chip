"""价格区间与股息率序列测试。"""

from __future__ import annotations

import pytest

from dividend.analysis import anchor_prices, build_daily_yield_series, price_zone, yield_quantiles


def _series(values: list[float | None]) -> list[dict]:
    """构造 {date, close, div_yield} 序列。"""
    return [
        {"date": f"2024-01-{i + 1:02d}", "close": 10.0, "dps_ttm": 1.0, "div_yield": v}
        for i, v in enumerate(values)
    ]


def test_quantiles_basic():
    qs = yield_quantiles(_series([4.0, 5.0, 6.0, 7.0, 8.0]))
    assert qs["50.0"] == 6.0
    assert qs["25.0"] == 5.0
    assert qs["75.0"] == 7.0
    # 线性插值: P10 = 4 + 0.4×(5-4), P90 = 7 + 0.6×(8-7)
    assert qs["10.0"] == pytest.approx(4.4)
    assert qs["90.0"] == pytest.approx(7.6)


def test_quantiles_empty():
    assert yield_quantiles([]) == {}


def test_zone_classification():
    qs = yield_quantiles(_series([4.0, 5.0, 6.0, 7.0, 8.0]))
    assert price_zone(8.0, qs) == "深度低估"  # ≥ P90=7.6
    assert price_zone(7.3, qs) == "低估"  # P75=7.0 ≤ y < P90
    assert price_zone(4.0, qs) == "深度高估"  # ≤ P10=4.4
    assert price_zone(4.7, qs) == "高估"  # P10 < y ≤ P25=5.0
    assert price_zone(6.0, qs) == "合理"


def test_zone_deep():
    qs = yield_quantiles(_series([2.0, 3.0, 5.0, 7.0, 9.0]))
    assert price_zone(9.0, qs) == "深度低估"
    assert price_zone(2.0, qs) == "深度高估"


def test_zone_missing():
    assert price_zone(None, {"50.0": 6.0}) == "合理"


def test_anchor_prices():
    """DPS=1.0, 股息率 7%(P50) → 中枢价 14.29; P95 线性插值 9.6% → 悲观价 10.42。"""
    series = _series([5.0, 6.0, 7.0, 8.0, 10.0])
    qs = yield_quantiles(series)
    result = anchor_prices(1.0, series, current_yield=8.0)
    assert result["zone"] == "低估"
    assert result["anchors"]["central"] == pytest.approx(1.0 / 0.07, abs=0.01)  # P50=7%
    assert qs["95.0"] == pytest.approx(9.6)
    assert result["anchors"]["pessimistic"] == pytest.approx(1.0 / 0.096, abs=0.01)  # P95=9.6%


def test_anchor_prices_no_dps():
    result = anchor_prices(0.0, _series([5.0, 6.0, 7.0, 8.0]))
    assert result["anchors"]["central"] is None
    assert result["zone"] == "合理"


def test_daily_yield_series_ttm_rolling():
    """TTM 股息: 除净日落在近 365 天内的现金计入, 跨年滚动。"""
    kline = [
        {"date": "2023-06-01", "close": 100.0},
        {"date": "2024-06-01", "close": 100.0},
        {"date": "2024-07-01", "close": 100.0},
    ]
    dividends = [
        {"ex_date": "2023-12-01", "cash_per_share": 3.0},
        {"ex_date": "2024-06-15", "cash_per_share": 4.0},  # 2024-07-01 时点在 TTM 内
    ]
    series = build_daily_yield_series(kline, dividends)
    # 2023-06-01: TTM 内无分红(2023-12-01 在 365 天后) → None
    assert series[0]["div_yield"] is None
    # 2024-06-01: 2023-12-01 在 TTM 内 → 3%
    assert series[1]["div_yield"] == 3.0
    # 2024-07-01: 两次分红都在 TTM 内 → 7%
    assert series[2]["div_yield"] == 7.0


def test_trailing_dps_excludes_special():
    """一次性特别股息默认从 TTM 剔除, 可显式纳入。"""
    from datetime import date

    from dividend.analysis.yield_series import trailing_dps

    dividends = [
        {"ex_date": "2024-03-01", "cash_per_share": 0.5, "special": False},
        {"ex_date": "2024-06-01", "cash_per_share": 2.5, "special": True},  # 特别派息
    ]
    as_of = date(2024, 12, 31)
    assert trailing_dps(dividends, as_of=as_of) == 0.5
    assert trailing_dps(dividends, as_of=as_of, exclude_special=False) == 3.0
