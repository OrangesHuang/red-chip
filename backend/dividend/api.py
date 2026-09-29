"""高股息分析领域 API: 股票池 / 个股详情 / 手动刷新 / 股票池管理。"""

from __future__ import annotations

import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from base.config import DEFAULT_STOCK_CODE, REFRESH_MIN_INTERVAL_SEC
from base.fetch.news import fetch_stock_news
from base.fetch.realtime import fetch_realtime
from base.pool import add_stock, get_stock, list_custom, remove_stock
from base.store.pool_repo import delete_stock_data, update_stock_name
from base.store.settings_repo import get_setting, set_setting
from dividend.analysis import build_zone_stats
from dividend.service import build_pool_live, build_stock_detail, refresh_one_stock

router = APIRouter(prefix="/api/dividend", tags=["dividend"])


class PoolAddRequest(BaseModel):
    code: str
    name: str | None = None
    market: str | None = None  # 留空自动推断(hk/sh/sz)
    industry: str | None = None


@router.get("/pool")
def pool():
    """股票池总览: 因子总分降序 + 实时行情叠加(实时失败降级用快照价)。"""
    rows = build_pool_live()
    return {"stocks": rows, "count": len(rows)}


@router.get("/pool/zone-stats")
def pool_zone_stats():
    """价格区间统计: 各区间数量/上涨下跌家数/胜率 + 等权组合综合涨跌。"""
    stats = build_zone_stats(build_pool_live())
    stats["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return stats


@router.get("/pool/custom")
def pool_custom():
    """用户自定义股票列表(不含内置池)。"""
    return {"stocks": list_custom()}


@router.post("/pool")
def pool_add(body: PoolAddRequest):
    """添加股票到池子(自动推断市场, 名称缺省时从实时行情补全), 并立即拉取数据。"""
    code = body.code.strip()
    name = (body.name or "").strip()
    ok, msg = add_stock(code, name or None, body.market, body.industry)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    if not name:
        # 名称自动补全: 股票须先入池, fetch_realtime 才能正确识别市场前缀
        try:
            rt = fetch_realtime([code])
            if rt and rt[0].get("name"):
                update_stock_name(code, str(rt[0]["name"]))
        except Exception:  # noqa: BLE001
            pass
    refresh = refresh_one_stock(code)
    return {"status": "ok", "message": msg, "refresh": refresh}


@router.delete("/pool/{code}")
def pool_remove(code: str):
    """移除自定义股票并清理其数据(内置股票不可删)。"""
    ok, msg = remove_stock(code)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    delete_stock_data(code)
    return {"status": "ok", "message": msg}


@router.get("/stock/{code}")
def stock_detail(code: str, days: int = Query(default=640, ge=60, le=3200)):
    if get_stock(code) is None:
        raise HTTPException(status_code=404, detail=f"unknown stock code: {code}")
    return build_stock_detail(code, kline_days=days)


@router.post("/stock/{code}/refresh")
def stock_refresh(code: str):
    """手动刷新单只股票(K线+分红+快照), 带最小间隔限流。"""
    if get_stock(code) is None:
        raise HTTPException(status_code=404, detail=f"unknown stock code: {code}")
    last = get_setting(f"last_refresh:{code}")
    if last:
        try:
            elapsed = time.time() - datetime.strptime(last, "%Y-%m-%d %H:%M:%S").timestamp()
            if elapsed < REFRESH_MIN_INTERVAL_SEC:
                return {"status": "skipped", "code": code, "retry_after_sec": int(REFRESH_MIN_INTERVAL_SEC - elapsed)}
        except ValueError:
            pass
    result = refresh_one_stock(code)
    set_setting(f"last_refresh:{code}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return {"status": "ok" if result["ok"] else "partial", "code": code, **result}


@router.get("/stock/{code}/kline")
def stock_kline(code: str, days: int = Query(default=640, ge=10, le=3200)):
    """仅 K 线(轻量, 供图表懒加载)。"""
    if get_stock(code) is None:
        raise HTTPException(status_code=404, detail=f"unknown stock code: {code}")
    detail = build_stock_detail(code, kline_days=days)
    return {"code": code, "name": detail["name"], "kline": detail["kline"]}


@router.get("/stock/{code}/news")
def stock_news(code: str, limit: int = Query(default=20, ge=1, le=50)):
    """个股资讯(标题/时间/来源/摘要/链接), 内存缓存 2 分钟。"""
    if get_stock(code) is None:
        raise HTTPException(status_code=404, detail=f"unknown stock code: {code}")
    info = get_stock(code) or {}
    return {"code": code, "name": info.get("name", code), "news": fetch_stock_news(code, limit)}


@router.get("/default")
def default_code():
    info = get_stock(DEFAULT_STOCK_CODE) or {"name": DEFAULT_STOCK_CODE}
    return {"code": DEFAULT_STOCK_CODE, "name": info["name"]}
