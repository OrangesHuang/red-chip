"""base/analysis: 跨领域共用纯函数(无 I/O)。

- position: 价格位置/分位数/均线等通用计算
- 领域私有逻辑(高股息因子/价格区间/赔率)在 dividend/analysis/, 不进 base
"""

from base.analysis.position import (
    percentile_rank,
    price_position,
    quantiles,
    sma,
)

__all__ = ["percentile_rank", "price_position", "quantiles", "sma"]
