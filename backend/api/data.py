"""数据管理 API: 数据状态 / 一键重建。"""

from __future__ import annotations

import os

from fastapi import APIRouter, Query

from base.config import DB_PATH
from base.pool import get_all_stocks
from base.store import dividend_repo, factor_repo, stock_repo
from dividend.service import refresh_all_stocks

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/status")
def data_status():
    """每只股票的数据覆盖情况 + 数据库体积。"""
    stocks = []
    for code, info in get_all_stocks().items():
        daily = stock_repo.daily_stats(code)
        div = dividend_repo.dividend_stats(code)
        snap = factor_repo.snapshot_dates(code, limit=1)
        stocks.append(
            {
                "code": code,
                "name": info["name"],
                "industry": info["industry"],
                "custom": bool(info.get("custom")),
                "daily_count": daily["cnt"],
                "daily_first": daily["first_date"],
                "daily_last": daily["last_date"],
                "dividend_count": div["cnt"],
                "dividend_last": div["last_date"],
                "snapshot_date": snap[-1]["date"] if snap else None,
            }
        )
    db_size = os.path.getsize(DB_PATH) if DB_PATH.exists() else 0
    return {"stocks": stocks, "db_size": db_size, "db_path": str(DB_PATH)}


@router.post("/rebuild")
def data_rebuild(days: int = Query(default=300, ge=60, le=2000)):
    """一键重建: 全池拉取 K 线 + 分红 + 因子快照(阻塞式, 约 1~2 分钟)。"""
    return refresh_all_stocks(backfill_days=days)
