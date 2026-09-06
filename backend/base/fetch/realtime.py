"""实时行情拉取: 腾讯 qt.gtimg.cn, A股(sh/sz)/港股(hk)通用。

symbol 按 config.STOCKS 的 market 字段生成。返回字段与 A 股同构
(第 4 个字段起: 现价/昨收/今开/成交量...), 港股成交量单位为「股」。
解析全部防御式: 任一字段缺失/非数值 → None, 不抛异常。
"""

from __future__ import annotations

import urllib.request

from base.config import HTTP_TIMEOUT, REALTIME_URL
from base.fetch.kline import market_symbol


def _safe_float(parts: list[str], idx: int) -> float | None:
    if idx >= len(parts):
        return None
    try:
        return float(parts[idx])
    except (ValueError, IndexError):
        return None


def _parse_line(line: str) -> dict | None:
    """解析形如 v_hk00941="200~中国移动~00941~66.95~..." 的单行。"""
    if "=" not in line:
        return None
    body = line.split("=", 1)[1].strip().strip('"')
    parts = body.split("~")
    if len(parts) < 35:
        return None
    return {
        "code": parts[2] if len(parts) > 2 else None,
        "name": parts[1] if len(parts) > 1 else None,
        "price": _safe_float(parts, 3),
        "prev_close": _safe_float(parts, 4),
        "open": _safe_float(parts, 5),
        "volume": _safe_float(parts, 36) or _safe_float(parts, 7),  # 手口径优先, 缺省回退股口径
        "amount": _safe_float(parts, 37),  # 万元
        "high": _safe_float(parts, 33) or _safe_float(parts, 41),
        "low": _safe_float(parts, 34) or _safe_float(parts, 42),
        "change": _safe_float(parts, 31),
        "change_pct": _safe_float(parts, 32),
        "turnover": _safe_float(parts, 38),  # 换手率 %
        "pe": _safe_float(parts, 39),
        "pb": _safe_float(parts, 46),
        "total_mv": _safe_float(parts, 45),  # 总市值(亿)
        "circ_mv": _safe_float(parts, 44),  # 流通市值(亿)
    }


def fetch_realtime(codes: list[str]) -> list[dict]:
    """批量拉取实时行情; 单只失败不影响其余, 返回空列表不抛异常。"""
    if not codes:
        return []
    symbols = ",".join(market_symbol(c) for c in codes)
    req = urllib.request.Request(REALTIME_URL.format(symbols=symbols), headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            raw = resp.read().decode("gbk", errors="ignore")
    except Exception as e:  # noqa: BLE001
        print(f"[FETCH] realtime {symbols} failed: {e}")
        return []
    result = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parsed = _parse_line(line)
        if parsed and parsed.get("price") is not None:
            result.append(parsed)
    return result
