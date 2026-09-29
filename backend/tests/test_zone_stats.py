"""价格区间统计(zone_stats)单测。"""

from __future__ import annotations

from dividend.analysis import build_zone_stats


def test_zone_counts_and_win_rate():
    rows = [
        {"zone": "低估", "change_pct": 2.0},
        {"zone": "低估", "change_pct": -1.0},
        {"zone": "低估", "change_pct": 0.0},
        {"zone": "高估", "change_pct": -3.0},
        {"zone": "高估", "change_pct": -0.5},
    ]
    stats = build_zone_stats(rows)
    zones = {z["zone"]: z for z in stats["zones"]}
    assert zones["低估"]["count"] == 3
    assert zones["低估"]["up"] == 1
    assert zones["低估"]["down"] == 1
    assert zones["低估"]["flat"] == 1
    # 胜率分母 = 有效家数(含持平) = 3
    assert zones["低估"]["win_rate"] == round(1 / 3 * 100, 1)
    assert zones["低估"]["avg_change"] == round((2.0 - 1.0 + 0.0) / 3, 4)
    assert zones["高估"]["win_rate"] == 0.0
    # 空区间也保留在结果中, 便于前端稳定成图
    assert zones["深度低估"]["count"] == 0
    assert zones["深度低估"]["win_rate"] is None


def test_missing_change_excluded_from_denominator():
    rows = [
        {"zone": "合理", "change_pct": None},
        {"zone": "合理", "change_pct": 1.5},
    ]
    stats = build_zone_stats(rows)
    zone = next(z for z in stats["zones"] if z["zone"] == "合理")
    assert zone["count"] == 2
    assert zone["valid"] == 1
    assert zone["win_rate"] == 100.0
    assert zone["avg_change"] == 1.5


def test_unknown_zone_bucketed_as_no_data():
    stats = build_zone_stats([{"zone": "", "change_pct": 1.0}, {"change_pct": -1.0}])
    zone = next(z for z in stats["zones"] if z["zone"] == "无数据")
    assert zone["count"] == 2


def test_overall_equal_weight_return_is_mean_change():
    """等权组合: 资金平分 5 只, 组合涨跌 = 各标的涨跌幅算术平均。"""
    rows = [
        {"zone": "低估", "change_pct": 3.0},
        {"zone": "低估", "change_pct": -1.0},
        {"zone": "合理", "change_pct": 2.0},
        {"zone": "高估", "change_pct": -2.0},
        {"zone": "高估", "change_pct": 1.0},
    ]
    overall = build_zone_stats(rows)["overall"]
    assert overall["count"] == 5
    assert overall["up"] == 3
    assert overall["down"] == 2
    assert overall["win_rate"] == 60.0
    assert overall["equal_weight_return"] == round((3.0 - 1.0 + 2.0 - 2.0 + 1.0) / 5, 4)


def test_zone_includes_stock_details():
    """每个区间返回标的明细, 供前端悬浮查看。"""
    rows = [
        {"code": "00941", "name": "中国移动", "market": "hk", "price": 80.0, "change_pct": 1.2, "zone": "低估"},
        {"code": "601088", "name": "中国神华", "market": "sh", "price": 40.0, "change_pct": -0.5, "zone": "低估"},
    ]
    zone = next(z for z in build_zone_stats(rows)["zones"] if z["zone"] == "低估")
    assert [s["code"] for s in zone["stocks"]] == ["00941", "601088"]
    assert zone["stocks"][0]["name"] == "中国移动"
    assert zone["stocks"][1]["change_pct"] == -0.5


def test_overall_empty():
    overall = build_zone_stats([])["overall"]
    assert overall["count"] == 0
    assert overall["win_rate"] is None
    assert overall["equal_weight_return"] is None
