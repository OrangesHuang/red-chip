"""dividend.service 纯 helper 单测(不触网)。"""

from __future__ import annotations

from dividend.service import _last_close_change_pct


def test_last_close_change_pct():
    assert _last_close_change_pct([{"close": 100.0}, {"close": 103.0}]) == 3.0
    assert _last_close_change_pct([{"close": 27.03}, {"close": 27.24}]) == 0.7769
    # 不足两根 / 前收为 0 / 收盘缺失 → None(不抛异常)
    assert _last_close_change_pct([]) is None
    assert _last_close_change_pct([{"close": 100.0}]) is None
    assert _last_close_change_pct([{"close": 0.0}, {"close": 1.0}]) is None
    assert _last_close_change_pct([{"close": 100.0}, {"close": None}]) is None
