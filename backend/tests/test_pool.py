"""股票池访问层测试: 市场推断与添加校验(纯逻辑, 不触库)。"""

from __future__ import annotations

from base.pool import add_stock, detect_market


def test_detect_market():
    assert detect_market("00941") == "hk"
    assert detect_market("600941") == "sh"
    assert detect_market("601398") == "sh"
    assert detect_market("000858") == "sz"
    assert detect_market("300750") == "sz"
    assert detect_market("830799") is None  # 北交所暂不支持
    assert detect_market("12345") == "hk"
    assert detect_market("1234567") is None  # 7 位非法


def test_add_stock_validation(monkeypatch):
    monkeypatch.setattr("base.pool.get_stock", lambda code: None)
    monkeypatch.setattr("base.pool._db_add", lambda *a, **k: True)

    ok, msg = add_stock("600276")
    assert ok
    assert "600276" in msg

    ok, msg = add_stock("  000333  ")  # 空白容错 + 自动市场
    assert ok

    ok, msg = add_stock("830799")  # 北交所, 无法推断市场
    assert not ok
    assert "市场" in msg

    ok, msg = add_stock("abc123")
    assert not ok

    ok, msg = add_stock("00941", market="sh")  # 明确市场时忽略推断
    assert ok


def test_add_stock_duplicate(monkeypatch):
    monkeypatch.setattr(
        "base.pool.get_stock",
        lambda code: {"name": "中国移动", "market": "hk"} if code == "00941" else None,
    )
    ok, msg = add_stock("00941")
    assert not ok
    assert "已在股票池" in msg
