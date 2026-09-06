"""高股息因子打分测试。"""

from __future__ import annotations

import pytest

from dividend.analysis import DividendInputs, factor_scores, grade_label, total_score


def test_high_quality_stock_scores_good():
    inp = DividendInputs(div_yield=7.0, div_years=10, div_growth=5.0, payout=50.0, debt=35.0, volatility=20.0)
    result = factor_scores(inp)
    assert result.total >= 75
    assert result.grade == "优质"


def test_low_quality_stock_scores_low():
    inp = DividendInputs(div_yield=2.0, div_years=1, div_growth=-10.0, payout=120.0, debt=90.0, volatility=65.0)
    result = factor_scores(inp)
    assert result.total < 45
    assert result.grade == "回避"


def test_missing_factors_renormalize():
    """财务因子缺失(未接入数据源)时仍可打分, 总分在 0~100。"""
    inp = DividendInputs(div_yield=6.5, div_years=8)
    result = factor_scores(inp)
    assert 0 <= result.total <= 100
    assert "payout" not in result.raw
    # 归一化后权重和 ≈ 1
    assert abs(sum(result.weights.values()) - 1.0) < 1e-9
    # 股息率权重占比提升(从 0.35 → 0.35/0.55)
    assert result.weights["div_yield"] > 0.5


def test_empty_inputs_graceful():
    result = factor_scores(DividendInputs())
    assert result.total == 0.0
    assert result.grade == "回避"


def test_yield_monotonic():
    """其他条件不变, 股息率越高总分越高。"""
    base = dict(div_years=8, div_growth=3.0, payout=50.0, debt=40.0, volatility=25.0)
    low = total_score(DividendInputs(div_yield=4.0, **base))
    mid = total_score(DividendInputs(div_yield=6.0, **base))
    high = total_score(DividendInputs(div_yield=8.0, **base))
    assert low < mid < high


def test_grade_boundaries():
    assert grade_label(75.0) == "优质"
    assert grade_label(74.9) == "良好"
    assert grade_label(60.0) == "良好"
    assert grade_label(59.9) == "一般"
    assert grade_label(45.0) == "一般"
    assert grade_label(44.9) == "回避"


def test_component_scores():
    inp = DividendInputs(div_yield=6.0, div_years=10, div_growth=5.0, payout=50.0, debt=20.0, volatility=20.0)
    result = factor_scores(inp)
    assert result.raw["div_yield"] >= 80
    assert result.raw["div_years"] == 100
    assert result.raw["div_growth"] == 100
    assert result.raw["payout"] == 100
    assert result.raw["debt"] == 100
    assert result.raw["volatility"] == 100
