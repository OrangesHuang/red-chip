"""分红数据规范化测试(A股/港股)。"""

from __future__ import annotations

import pandas as pd
import pytest

from base.fetch.dividend import _normalize_a_share, _parse_plan


def _a_share_df(rows: list[dict]) -> pd.DataFrame:
    cols = [
        "报告期", "送转股份-送转总比例", "送转股份-送股比例", "送转股份-转股比例",
        "现金分红-现金分红比例", "现金分红-现金分红比例描述", "方案进度",
        "除权除息日", "股权登记日", "最新公告日期",
    ]
    data = {c: [r.get(c) for r in rows] for c in cols}
    return pd.DataFrame(data)


def test_a_share_normalize_cash():
    """每10股派45.24元(含税) → 每股 4.524 元人民币。"""
    df = _a_share_df(
        [
            {
                "报告期": "2024-12-31",
                "现金分红-现金分红比例": 45.24,
                "现金分红-现金分红比例描述": "10派45.24元(含税,扣税后X元)",
                "除权除息日": "2025-06-20",
                "最新公告日期": "2025-05-10",
                "方案进度": "实施分配",
            }
        ]
    )
    rows = _normalize_a_share(df)
    assert len(rows) == 1
    r = rows[0]
    assert r["cash_per_share"] == pytest.approx(4.524)
    assert r["currency"] == "CNY"
    assert r["year"] == 2024
    assert r["ex_date"] == "2025-06-20"
    assert r["special"] is False


def test_a_share_normalize_bonus_and_drop():
    """送转比例折算每股; 无除权日/无现金无送转的行丢弃。"""
    df = _a_share_df(
        [
            {"报告期": "2023-12-31", "送转股份-送转总比例": 3.0, "除权除息日": "2024-05-10"},
            {"报告期": "2024-12-31", "现金分红-现金分红比例": 6.0, "除权除息日": None},  # 未实施
            {"报告期": "2022-12-31", "除权除息日": "2023-06-01"},  # 无现金无送转
        ]
    )
    rows = _normalize_a_share(df)
    assert len(rows) == 1
    assert rows[0]["bonus_ratio"] == pytest.approx(0.3)
    assert rows[0]["cash_per_share"] is None


def test_hk_plan_parse_variants():
    assert _parse_plan("每股派港币2.4元")[0] == 2.4
    assert _parse_plan("10派人民币3.2元")[0] == pytest.approx(0.352)  # 3.2/10 × FX_RMB_HKD
    assert _parse_plan("每股派人民币2.51元(相当于港币2.9003元)")[0] == 2.9003
    assert _parse_plan("每股派美元0.08元")[0] == pytest.approx(0.624)  # 0.08 × FX_USD_HKD
    assert _parse_plan("不派息")[0] is None
