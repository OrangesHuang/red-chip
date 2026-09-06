"""stock_daily / stock_realtime 仓储。"""

from __future__ import annotations

from base.store.database import get_connection


def upsert_daily(code: str, name: str, bars: list[dict]) -> int:
    """批量写入日线(按 date+code 覆盖), 返回写入条数。"""
    if not bars:
        return 0
    conn = get_connection()
    try:
        rows = []
        for i, bar in enumerate(bars):
            prev_close = bars[i - 1]["close"] if i > 0 else None
            change_pct = None
            if prev_close and prev_close > 0:
                change_pct = round((bar["close"] / prev_close - 1.0) * 100.0, 4)
            rows.append(
                (
                    bar["date"],
                    code,
                    name,
                    bar.get("open"),
                    bar.get("high"),
                    bar.get("low"),
                    bar.get("close"),
                    change_pct,
                    bar.get("volume"),
                    bar.get("amount"),
                )
            )
        conn.executemany(
            """
            INSERT INTO stock_daily
                (date, code, name, open_price, high_price, low_price, close_price,
                 change_pct, volume, amount, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(date, code) DO UPDATE SET
                name=excluded.name, open_price=excluded.open_price,
                high_price=excluded.high_price, low_price=excluded.low_price,
                close_price=excluded.close_price, change_pct=excluded.change_pct,
                volume=excluded.volume, amount=excluded.amount,
                updated_at=datetime('now','localtime')
            """,
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def get_daily(code: str, limit: int = 640) -> list[dict]:
    """最近 limit 条日线, 日期升序(旧→新)。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT date, name, open_price, high_price, low_price, close_price,
                   change_pct, volume, amount
            FROM stock_daily WHERE code = ?
            ORDER BY date DESC LIMIT ?
            """,
            (code, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    rows.reverse()
    return rows


def latest_daily(code: str) -> dict | None:
    """最新一条日线, 无则 None。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT date, name, open_price, high_price, low_price, close_price,
                   change_pct, volume, amount
            FROM stock_daily WHERE code = ?
            ORDER BY date DESC LIMIT 1
            """,
            (code,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_daily_since(code: str, since_date: str) -> list[dict]:
    """since_date(不含)之后的日线, 日期升序。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT date, name, open_price, high_price, low_price, close_price,
                   change_pct, volume, amount
            FROM stock_daily WHERE code = ? AND date > ?
            ORDER BY date ASC
            """,
            (code, since_date),
        )
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return rows


def upsert_realtime(rt: dict) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO stock_realtime
                (timestamp, code, price, change_pct, volume, amount, high, low, turnover, pe, pb)
            VALUES (datetime('now','localtime'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rt.get("code"),
                rt.get("price"),
                rt.get("change_pct"),
                rt.get("volume"),
                rt.get("amount"),
                rt.get("high"),
                rt.get("low"),
                rt.get("turnover"),
                rt.get("pe"),
                rt.get("pb"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def latest_realtime(code: str) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT timestamp, code, price, change_pct, volume, amount, high, low,
                   turnover, pe, pb
            FROM stock_realtime WHERE code = ?
            ORDER BY timestamp DESC LIMIT 1
            """,
            (code,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def daily_stats(code: str) -> dict:
    """数据覆盖统计: 条数/最早日期/最晚日期。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT COUNT(*) AS cnt, MIN(date) AS first_date, MAX(date) AS last_date
            FROM stock_daily WHERE code = ?
            """,
            (code,),
        )
        row = cur.fetchone()
        return dict(row) if row else {"cnt": 0, "first_date": None, "last_date": None}
    finally:
        conn.close()
