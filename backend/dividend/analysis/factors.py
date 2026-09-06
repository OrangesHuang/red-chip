"""高股息六因子打分(纯函数)。

六因子(权重见 config.FACTOR_WEIGHTS), 每因子 0~100:
    div_yield   滚动股息率 %      —— 越高的分红回报越好
    div_years   连续分红年数      —— 分红持续性
    div_growth  近 3 年每股股息 CAGR % —— 分红成长性
    payout      派息率 %         —— 健康区间 30~70(过高难持续, 过低成长弱)
    debt        资产负债率 %      —— 越低财务越稳健
    volatility  年化波动率 %      —— 越低走势越稳

每个因子按 config 中的折线锚点做线性插值。缺失因子 → 权重按剩余权重
重新归一化(优雅降级, 如财务数据未接入时 payout/debt 缺失仍可打分)。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from base.config import (
    DEBT_CURVE,
    DIV_GROWTH_CURVE,
    DIV_YEARS_CURVE,
    DIV_YIELD_CURVE,
    FACTOR_WEIGHTS,
    PAYOUT_CURVE,
    SCORE_FAIR,
    SCORE_FINE,
    SCORE_GOOD,
    VOLATILITY_CURVE,
)


@dataclass
class DividendInputs:
    div_yield: float | None = None  # 滚动 TTM 股息率 %
    div_years: int | None = None  # 连续分红年数
    div_growth: float | None = None  # 近 3 年每股股息 CAGR %
    payout: float | None = None  # 派息率 %
    debt: float | None = None  # 资产负债率 %
    volatility: float | None = None  # 年化波动率 %


@dataclass
class FactorScores:
    raw: dict[str, float] = field(default_factory=dict)  # 各因子 0~100
    weights: dict[str, float] = field(default_factory=dict)  # 实际使用的归一化权重
    total: float = 0.0  # 加权总分 0~100
    grade: str = "回避"  # 优质/良好/一般/回避


def _interp(curve: list[tuple[float, float]], x: float) -> float:
    """折线线性插值; 超出两端按端点截断。"""
    if x <= curve[0][0]:
        return float(curve[0][1])
    if x >= curve[-1][0]:
        return float(curve[-1][1])
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]
        x1, y1 = curve[i]
        if x <= x1:
            frac = (x - x0) / (x1 - x0) if x1 != x0 else 0.0
            return round(y0 + (y1 - y0) * frac, 1)
    return float(curve[-1][1])


def _score_component(name: str, value: float | None) -> float | None:
    if value is None:
        return None
    if name == "div_yield":
        return _interp(DIV_YIELD_CURVE, value)
    if name == "div_years":
        return _interp(DIV_YEARS_CURVE, value)
    if name == "div_growth":
        return _interp(DIV_GROWTH_CURVE, value)
    if name == "payout":
        return _interp(PAYOUT_CURVE, value)
    if name == "debt":
        return _interp(DEBT_CURVE, value)
    if name == "volatility":
        return _interp(VOLATILITY_CURVE, value)
    return None


def factor_scores(inp: DividendInputs) -> FactorScores:
    """计算各因子得分 + 归一化权重 + 总分 + 等级。"""
    raw: dict[str, float] = {}
    weights: dict[str, float] = {}
    for name, weight in FACTOR_WEIGHTS.items():
        value = getattr(inp, name)
        score = _score_component(name, value)
        if score is not None:
            raw[name] = score
            weights[name] = weight

    total_w = sum(weights.values())
    if total_w <= 0:
        return FactorScores(raw=raw, weights=weights, total=0.0, grade=grade_label(0.0))

    normalized = {name: w / total_w for name, w in weights.items()}
    total = round(sum(score * normalized[name] for name, score in raw.items()), 1)
    return FactorScores(raw=raw, weights=normalized, total=total, grade=grade_label(total))


def total_score(inp: DividendInputs) -> float:
    return factor_scores(inp).total


def grade_label(score: float) -> str:
    if score >= SCORE_GOOD:
        return "优质"
    if score >= SCORE_FINE:
        return "良好"
    if score >= SCORE_FAIR:
        return "一般"
    return "回避"
