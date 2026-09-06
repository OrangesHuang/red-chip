"""赔率计算(纯函数): 上行空间 ÷ 下行空间。

以股息率历史分位为锚:
    中枢价 central     = dps ÷ 股息率 P50 —— 「估值回到历史中枢」的目标价
    乐观价 optimistic  = dps ÷ 股息率 P25 —— 「估值回到较贵端」的上限参考
    悲观价 pessimistic = dps ÷ 股息率 P95 —— 「估值走到最便宜端」的支撑价

    上行空间 = central / 现价 - 1(保守用中枢, 不用乐观价)
    下行空间 = 1 - pessimistic / 现价(现价到悲观支撑的潜在回撤)
    赔率     = 上行空间 / 下行空间

现价 ≤ 悲观价 → 下行空间 ≤ 0 → 赔率封顶 ODDS_FLOOR_CAP(几乎无下行风险)。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from base.config import ODDS_FLOOR_CAP, ODDS_HIGH, ODDS_MID
from dividend.analysis.range import anchor_prices


@dataclass
class OddsResult:
    current_price: float
    central_price: float | None
    optimistic_price: float | None
    pessimistic_price: float | None
    upside_pct: float | None  # 上行空间 %
    downside_pct: float | None  # 下行空间 %(正数表示潜在回撤)
    odds: float | None  # 赔率
    grade: str = "低赔率"
    note: str = ""


def odds(current_price: float, annual_dps: float, yield_series: list[dict]) -> OddsResult:
    """计算赔率。数据不足(无 yield 序列/无 DPS/现价无效)时各值置 None 不抛异常。"""
    result = OddsResult(
        current_price=current_price,
        central_price=None,
        optimistic_price=None,
        pessimistic_price=None,
        upside_pct=None,
        downside_pct=None,
        odds=None,
    )
    if current_price is None or current_price <= 0:
        result.note = "现价缺失"
        return result

    anchors = anchor_prices(annual_dps, yield_series)
    central = anchors["anchors"]["central"]
    pessimistic = anchors["anchors"]["pessimistic"]
    optimistic = anchors["anchors"]["optimistic"]
    result.central_price = central
    result.optimistic_price = optimistic
    result.pessimistic_price = pessimistic
    result.note = anchors["zone"]

    if central is None or pessimistic is None:
        result.note = "股息率历史不足, 无法锚定赔率"
        return result

    upside = central / current_price - 1.0
    downside = 1.0 - pessimistic / current_price
    result.upside_pct = round(upside * 100.0, 2)
    result.downside_pct = round(downside * 100.0, 2)

    if downside <= 0.02:
        result.odds = ODDS_FLOOR_CAP
        result.grade = "高赔率"
        result.downside_pct = 0.0  # 现价已低于悲观支撑价, 下行空间归零
        result.note = "现价已低于悲观支撑价, 下行空间趋零"
        return result
    result.odds = round(upside / downside, 2)
    result.grade = odds_grade(result.odds)
    return result


def odds_grade(ratio: float | None) -> str:
    if ratio is None:
        return "低赔率"
    if ratio >= ODDS_HIGH:
        return "高赔率"
    if ratio >= ODDS_MID:
        return "中等赔率"
    return "低赔率"
