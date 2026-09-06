"""赔率计算测试。"""

from __future__ import annotations

import pytest

from dividend.analysis import odds, odds_grade


def _series(yields: list[float]) -> list[dict]:
    return [{"date": f"2024-01-{i + 1:02d}", "close": 10.0, "dps_ttm": 1.0, "div_yield": v} for i, v in enumerate(yields)]


def test_cheap_stock_high_odds():
    """现价便宜(股息率高于中枢) → 上行空间为正, 赔率 > 1。"""
    # 序列 [4,4.5,5,5.5,6,8]: P50=5.25 → 中枢价 19.05; P95=7.5 → 悲观价 13.33
    series = _series([4.0, 4.5, 5.0, 5.5, 6.0, 8.0])
    result = odds(current_price=15.0, annual_dps=1.0, yield_series=series)
    assert result.central_price == pytest.approx(1.0 / 0.0525, abs=0.01)
    assert result.pessimistic_price == pytest.approx(1.0 / 0.075, abs=0.01)
    assert result.upside_pct is not None and result.upside_pct > 0
    assert result.downside_pct is not None and result.downside_pct > 0
    # 上行 19.05/15-1 = 26.98%, 下行 1-13.33/15 = 11.11% → 赔率 ≈ 2.43
    assert result.odds == pytest.approx(2.43, abs=0.02)


def test_expensive_stock_low_odds():
    """现价贵(股息率低于中枢) → 上行空间为负, 赔率 < 1 或为负。"""
    series = _series([4.0, 4.5, 5.0, 5.5, 6.0])
    result = odds(current_price=25.0, annual_dps=1.0, yield_series=series)  # 股息率 4% < 中枢 5%
    assert result.upside_pct is not None and result.upside_pct < 0
    assert result.odds is not None and result.odds < 1.0


def test_below_pessimistic_price_capped():
    """现价 ≤ 悲观价 → 下行空间趋零, 赔率封顶。"""
    series = _series([4.0, 5.0, 6.0, 7.0, 8.0, 10.0])  # P95 = 10% → 悲观价 10
    result = odds(current_price=9.0, annual_dps=1.0, yield_series=series)
    assert result.odds == 99.0
    assert result.grade == "高赔率"


def test_missing_data_graceful():
    result = odds(current_price=0, annual_dps=1.0, yield_series=_series([5.0]))
    assert result.odds is None
    result2 = odds(current_price=10.0, annual_dps=1.0, yield_series=[])
    assert result2.odds is None


def test_odds_grade():
    assert odds_grade(3.0) == "高赔率"
    assert odds_grade(2.0) == "中等赔率"
    assert odds_grade(1.4) == "低赔率"
    assert odds_grade(None) == "低赔率"
