"""日 K 线拉取: 腾讯主源 + 新浪降级源, 支持 A 股(sh/sz)与港股(hk)。

symbol 按股票池(内置 config + 自定义)的 market 字段生成: hk→hk{5位代码}, sh→sh{6位代码},
sz→sz{6位代码}。支持:
- 最近 N 根(腾讯接口单次上限约 640~700 根)
- 日期区间拉取(历史回填), 超上限自动按自然日分块合并, 避免截断缺口
"""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timedelta

from base.config import (
    HTTP_TIMEOUT,
    KLINE_CACHE_TTL_SEC,
    KLINE_FAIL_COOLDOWN_SEC,
    KLINE_LIMIT,
    KLINE_URL,
    KLINE_URL_ALT,
    KLINE_URL_RANGE,
    KLINE_URL_RANGE_ALT,
    RANGE_CHUNK_NATURAL_DAYS,
    SINA_HK_KLINE_URL,
)
from base.pool import get_stock

# 新浪 A 股日K(未复权): symbol=sh600941
SINA_CN_KLINE_URL = (
    "https://quotes.sina.cn/cn/api/json_v2.php/"
    "CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={limit}"
)

# 区间接口单次响应上限约 640~700 根, 分块每块自然日跨度需保证交易日数 ≤ 安全上限
RANGE_CHUNK_LIMIT = 650

_CACHE: dict[tuple, tuple[float, list[dict] | None]] = {}


def _cached(code: str, limit: int, start_date: str | None = None, end_date: str | None = None):
    """内存 TTL 缓存: 有效期内直接返回, 失败也冷却缓存避免重试风暴。"""
    key = (code, limit, start_date, end_date)
    now = time.time()
    hit = _CACHE.get(key)
    if hit is None:
        return None
    ts, data = hit
    if data is None:
        if now - ts < KLINE_FAIL_COOLDOWN_SEC:
            return data
    elif now - ts < KLINE_CACHE_TTL_SEC:
        return data
    _CACHE.pop(key, None)
    return None


def _store(code: str, limit: int, data: list[dict] | None, start_date: str | None = None, end_date: str | None = None) -> None:
    _CACHE[(code, limit, start_date, end_date)] = (time.time(), data)


def market_of(code: str) -> str:
    """代码 → 市场(hk/sh/sz); 未知代码默认 hk(与旧行为兼容)。"""
    info = get_stock(code)
    return info["market"] if info else "hk"


def market_symbol(code: str) -> str:
    """证券代码 → 腾讯 symbol: hk00941 / sh600941 / sz000858。"""
    return f"{market_of(code)}{code}"


def _iter_date_windows(start_date: str, end_date: str) -> list[tuple[str, str]]:
    """[start_date, end_date] 按自然日切块(每块 ≤ RANGE_CHUNK_NATURAL_DAYS 天)。"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    windows: list[tuple[str, str]] = []
    cur = start
    while cur <= end:
        win_end = min(cur + timedelta(days=RANGE_CHUNK_NATURAL_DAYS), end)
        windows.append((cur.strftime("%Y-%m-%d"), win_end.strftime("%Y-%m-%d")))
        cur = win_end + timedelta(days=1)
    return windows


def _parse_tencent_rows(symbol: str, data: dict) -> list[dict]:
    node = data.get("data", {}).get(symbol, {})
    rows = node.get("day") or node.get("qfqday") or []
    result = []
    for r in rows:
        if len(r) < 6 or not r[0]:
            continue
        result.append(
            {
                "date": r[0],
                "open": float(r[1]),
                "close": float(r[2]),
                "high": float(r[3]),
                "low": float(r[4]),
                "volume": float(r[5]),
            }
        )
    return result


def _fetch_tencent(symbol: str, url: str, alt_url: str | None = None) -> list[dict] | None:
    """腾讯 K 线 GET + 解析; 主域名失败自动换备用域名, 全部失败返回 None。

    腾讯偶发对单个域名整体 501(如 web.ifzq 曾整段不可用), 双域名互备可显著
    提高可用性。
    """
    for i, u in enumerate((url, alt_url)):
        if not u:
            continue
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            rows = _parse_tencent_rows(symbol, data)
            if rows:
                return rows
        except Exception as e:  # noqa: BLE001
            print(f"[FETCH] kline {symbol} {'主' if i == 0 else '备用'}域名失败: {e}")
    return None


def _fetch_sina(code: str, limit: int) -> list[dict] | None:
    """新浪日K(未复权): 腾讯不可达时的降级源。A股 symbol=sh600941, 港股=5位代码。"""
    market = market_of(code)
    if market == "hk":
        symbol = code  # 港股新浪接口用 5 位代码无前缀
        url = SINA_HK_KLINE_URL.format(code=symbol, limit=limit)
    else:
        symbol = market_symbol(code)  # A股用 sh/sz 前缀
        url = SINA_CN_KLINE_URL.format(symbol=symbol, limit=limit)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"[FETCH] kline sina {code} failed: {e}")
        return None
    if not isinstance(data, list) or not data:
        return None
    result = []
    for r in data:
        if not r.get("day"):
            continue
        result.append(
            {
                "date": r["day"],
                "open": float(r["open"]),
                "close": float(r["close"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "volume": float(r["volume"]),
            }
        )
    return result or None


def fetch_kline(code: str, limit: int = KLINE_LIMIT, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """拉取日K线(前复权), A股/港股通用。

    不带日期: 返回最近 limit 根; 带日期: 返回 [start_date, end_date] 区间内全部 K 线,
    超过单次上限自动分块合并。失败/无数据返回空列表, 不抛异常。
    """
    cached = _cached(code, limit, start_date, end_date)
    if cached is not None:
        return cached

    symbol = market_symbol(code)

    if start_date or end_date:
        s = start_date or "2000-01-01"
        e = end_date or datetime.now().strftime("%Y-%m-%d")
        merged: list[dict] = []
        tencent_ok = False
        for ws, we in _iter_date_windows(s, e):
            url = KLINE_URL_RANGE.format(symbol=symbol, start=ws, end=we, limit=RANGE_CHUNK_LIMIT)
            alt = KLINE_URL_RANGE_ALT.format(symbol=symbol, start=ws, end=we, limit=RANGE_CHUNK_LIMIT)
            bars = _fetch_tencent(symbol, url, alt) or []
            if bars:
                tencent_ok = True
            else:
                print(f"[FETCH] kline {code} 区间 {ws}~{we} 无数据")
            merged.extend(bars)
        if not tencent_ok and market_of(code) != "hk":
            # A 股降级: 新浪 CN 接口支持大 datalen, 直接取最近 limit 根(日期近似, 未复权)
            bars = _fetch_sina(code, max(limit, RANGE_CHUNK_LIMIT)) or []
            if bars:
                print(f"[FETCH] kline {code} 腾讯区间失败, 降级新浪最近 {len(bars)} 根")
                merged = bars
        seen: set[str] = set()
        result: list[dict] = []
        for r in sorted(merged, key=lambda x: x["date"]):
            if r["date"] not in seen:
                seen.add(r["date"])
                result.append(r)
        _store(code, limit, result, start_date, end_date)
        return result

    url = KLINE_URL.format(symbol=symbol, limit=limit)
    alt = KLINE_URL_ALT.format(symbol=symbol, limit=limit)
    recent_bars: list[dict] | None = _fetch_tencent(symbol, url, alt)
    if recent_bars is None:
        recent_bars = _fetch_sina(code, limit)
    if recent_bars is None:
        recent_bars = []
    _store(code, limit, recent_bars, start_date, end_date)
    return recent_bars
