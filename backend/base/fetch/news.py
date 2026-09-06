"""个股资讯拉取: A股东财(akshare, 内容含摘要/来源) + 腾讯新闻(A/H 通用兜底)。

资讯为瞬态数据(不进 SQLite), 内存 TTL 缓存防重复请求。全部失败返回空列表。
规范化结构: {title, time, source, content(摘要), url}, 按时间倒序。
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.parse

from base.config import HTTP_TIMEOUT
from base.fetch.kline import market_of, market_symbol

NEWS_TTL_SEC = 120  # 资讯缓存有效期(秒)
NEWS_LIMIT = 20

# 腾讯新闻搜索: type=1(全部) + page=0(最新页); symbol=hk00941/sh600519
TENCENT_NEWS_URL = (
    "https://proxy.finance.qq.com/ifzqgtimg/appstock/news/info/search"
    "?symbol={symbol}&n={limit}&type=1&page=0"
)

_CACHE: dict[str, tuple[float, list[dict]]] = {}


def _cached(key: str):
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < NEWS_TTL_SEC:
        return hit[1]
    return None


def _store(key: str, rows: list[dict]) -> None:
    _CACHE[key] = (time.time(), rows)


def _fetch_em_news(code: str, limit: int) -> list[dict]:
    """东财个股新闻(akshare): 关键词/新闻标题/新闻内容/发布时间/文章来源/新闻链接。"""
    try:
        import akshare as ak
    except ImportError:
        return []
    fn = getattr(ak, "stock_news_em", None)
    if fn is None:
        return []
    try:
        df = fn(symbol=code)
    except Exception as e:  # noqa: BLE001
        print(f"[FETCH] news em {code} failed: {e}")
        return []
    if df is None or getattr(df, "empty", True):
        return []
    rows: list[dict] = []
    for _, row in df.head(limit).iterrows():
        title = str(row.get("新闻标题") or "").strip()
        if not title:
            continue
        rows.append(
            {
                "title": title[:120],
                "time": str(row.get("发布时间") or "").strip()[:19],
                "source": str(row.get("文章来源") or "东方财富").strip()[:30],
                "content": str(row.get("新闻内容") or "").strip()[:200],
                "url": str(row.get("新闻链接") or "").strip(),
            }
        )
    return rows


def _fetch_tencent_news(code: str, limit: int) -> list[dict]:
    """腾讯个股新闻(A/H 通用): id/symbol/title/time/type/url。"""
    url = TENCENT_NEWS_URL.format(symbol=market_symbol(code), limit=limit)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"[FETCH] news tencent {code} failed: {e}")
        return []
    items = (data.get("data") or {}).get("data") or []
    rows: list[dict] = []
    seen: set[str] = set()
    for it in items:
        title = str(it.get("title") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        rows.append(
            {
                "title": title[:120],
                "time": str(it.get("time") or "").strip()[:19],
                "source": "腾讯新闻",
                "content": "",
                "url": str(it.get("url") or "").strip(),
            }
        )
    return rows


def fetch_stock_news(code: str, limit: int = NEWS_LIMIT) -> list[dict]:
    """拉取个股资讯, 按时间倒序。A股优先东财, 失败降级腾讯; 港股直接腾讯。"""
    key = f"{code}:{limit}"
    cached = _cached(key)
    if cached is not None:
        return cached

    rows: list[dict] = []
    if market_of(code) != "hk":
        rows = _fetch_em_news(code, limit)
    if not rows:
        rows = _fetch_tencent_news(code, limit)
    _store(key, rows)
    return rows
