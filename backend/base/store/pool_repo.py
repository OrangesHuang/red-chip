"""custom_stocks 表仓储: 用户自定义股票(页面自助添加)。"""

from __future__ import annotations

from base.store.database import get_connection


def get_custom_stocks() -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT code, name, industry, market, created_at FROM custom_stocks ORDER BY created_at DESC"
        )
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return rows


def add_custom_stock(code: str, name: str, market: str, industry: str | None = None) -> bool:
    """插入自定义股票; 已存在返回 False(不覆盖)。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO custom_stocks (code, name, industry, market)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(code) DO NOTHING
            """,
            (code, name, industry, market),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def update_stock_name(code: str, name: str) -> None:
    """更新自定义股票名称(添加时名称自动补全用)。"""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE custom_stocks SET name = ? WHERE code = ?",
            (name, code),
        )
        conn.commit()
    finally:
        conn.close()


def remove_custom_stock(code: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM custom_stocks WHERE code = ?", (code,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_stock_data(code: str) -> None:
    """删除某股票的全部数据(移除股票池时清理, 防孤儿数据)。"""
    conn = get_connection()
    try:
        for table in ("stock_daily", "stock_realtime", "dividend", "factor_snapshot"):
            conn.execute(f"DELETE FROM {table} WHERE code = ?", (code,))
        conn.commit()
    finally:
        conn.close()
