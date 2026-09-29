"""dividend/analysis: 高股息个股分析领域 — 全部纯函数(无 I/O)。

- yield_series: 逐日 TTM 股息率序列(由 K 线与分红历史重构)
- factors: 高股息六因子打分
- range: 股息率锚定的价格区间
- odds: 赔率(上行/下行空间)
- zone_stats: 价格区间分布与等权综合胜率统计
"""

from dividend.analysis.factors import (
    DividendInputs,
    factor_scores,
    grade_label,
    total_score,
)
from dividend.analysis.odds import OddsResult, odds, odds_grade
from dividend.analysis.range import price_zone, yield_quantiles, anchor_prices
from dividend.analysis.yield_series import build_daily_yield_series, trailing_dps
from dividend.analysis.zone_stats import build_zone_stats

__all__ = [
    "DividendInputs",
    "factor_scores",
    "grade_label",
    "total_score",
    "OddsResult",
    "odds",
    "odds_grade",
    "price_zone",
    "yield_quantiles",
    "anchor_prices",
    "build_daily_yield_series",
    "trailing_dps",
    "build_zone_stats",
]
