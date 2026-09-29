"""价格区间统计(纯函数)。

按股息率锚定的价格区间(zone)汇总:
- 各区间的标的数量、当日上涨/下跌/持平家数、胜率(上涨家数 / 有效家数);
- 每个区间下的标的明细(代码/名称/市场/涨跌幅/现价), 供前端悬浮查看;
- 等权组合的口径: 把资金平均分配到所有标的, 组合当日涨跌 = 各标的涨跌幅均值
  (等权收益率的算术平均), 并给出全池综合胜率。

胜率分母为「有效家数」(当日有涨跌幅的标的), 涨跌幅缺失者不计入分母也不计入均值。
"""

from __future__ import annotations

# 区间从「最值得买」到「最贵」排序, 无数据垫底(与前端排序口径一致)
ZONE_ORDER = ["深度低估", "低估", "合理", "高估", "深度高估", "无数据"]


def _empty_bucket() -> dict:
    return {"count": 0, "up": 0, "down": 0, "flat": 0, "valid": 0, "change_sum": 0.0, "stocks": []}


def _stock_row(row: dict) -> dict:
    """区间明细: 前端悬浮模态框展示用。"""
    return {
        "code": row.get("code"),
        "name": row.get("name"),
        "market": row.get("market"),
        "price": row.get("price"),
        "change_pct": row.get("change_pct"),
    }


def build_zone_stats(rows: list[dict]) -> dict:
    """输入股票池行(含 zone / change_pct), 输出区间统计 + 等权综合口径。

    返回: {zones:[{zone,count,up,down,flat,valid,win_rate,avg_change}], overall:{...}}
    win_rate / avg_change 为百分数; 无有效涨跌幅时为 None。
    """
    buckets = {z: _empty_bucket() for z in ZONE_ORDER}
    for row in rows:
        zone = row.get("zone") or "无数据"
        if zone not in buckets:
            zone = "无数据"
        bucket = buckets[zone]
        bucket["count"] += 1
        bucket["stocks"].append(_stock_row(row))
        change = row.get("change_pct")
        if change is None:
            continue
        change = float(change)
        bucket["valid"] += 1
        bucket["change_sum"] += change
        if change > 0:
            bucket["up"] += 1
        elif change < 0:
            bucket["down"] += 1
        else:
            bucket["flat"] += 1

    zones = []
    for zone in ZONE_ORDER:
        b = buckets[zone]
        zones.append(
            {
                "zone": zone,
                "count": b["count"],
                "up": b["up"],
                "down": b["down"],
                "flat": b["flat"],
                "valid": b["valid"],
                "win_rate": round(b["up"] / b["valid"] * 100.0, 1) if b["valid"] else None,
                "avg_change": round(b["change_sum"] / b["valid"], 4) if b["valid"] else None,
                "stocks": b["stocks"],
            }
        )

    total = sum(b["count"] for b in buckets.values())
    valid = sum(b["valid"] for b in buckets.values())
    up = sum(b["up"] for b in buckets.values())
    down = sum(b["down"] for b in buckets.values())
    flat = sum(b["flat"] for b in buckets.values())
    change_sum = sum(b["change_sum"] for b in buckets.values())
    overall = {
        "count": total,
        "up": up,
        "down": down,
        "flat": flat,
        "valid": valid,
        "win_rate": round(up / valid * 100.0, 1) if valid else None,
        "equal_weight_return": round(change_sum / valid, 4) if valid else None,
    }
    return {"zones": zones, "overall": overall}
