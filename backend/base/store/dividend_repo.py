"""dividend 表仓储: 分红历史(按股票整体替换 + 查询)。"""

from __future__ import annotations

from base.store.database import get_connection


def replace_dividends(code: str, records: list[dict]) -> int:
    """整体替换某股票的分红历史(分红表小, 刷新即替换, 避免口径漂移), 返回条数。

    按 (ex_date, cash_per_share, bonus_ratio) 去重, 兼容数据源偶发重复行。
    """
    conn = get_connection()
    try:
        conn.execute("DELETE FROM dividend WHERE code = ?", (code,))
        seen: set[tuple] = set()
        rows = []
        for r in records:
            key = (r.get("ex_date"), r.get("cash_per_share"), r.get("bonus_ratio"))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                (
                    code,
                    r.get("year"),
                    r.get("announce_date"),
                    r.get("ex_date"),
                    r.get("pay_date"),
                    r.get("cash_per_share"),
                    r.get("currency"),
                    r.get("bonus_ratio"),
                    1 if r.get("special") else 0,
                    r.get("note"),
                )
            )
        conn.executemany(
            """
            INSERT INTO dividend (code, year, announce_date, ex_date, pay_date,
                                  cash_per_share, currency, bonus_ratio, special, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def get_dividends(code: str) -> list[dict]:
    """某股票全部分红, 按除净日倒序。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT code, year, announce_date, ex_date, pay_date,
                   cash_per_share, currency, bonus_ratio, special, note
            FROM dividend WHERE code = ?
            ORDER BY (ex_date IS NULL), ex_date DESC
            """,
            (code,),
        )
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return rows


def dividend_stats(code: str) -> dict:
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT COUNT(*) AS cnt, MIN(ex_date) AS first_date, MAX(ex_date) AS last_date "
            "FROM dividend WHERE code = ?",
            (code,),
        )
        row = cur.fetchone()
        return dict(row) if row else {"cnt": 0, "first_date": None, "last_date": None}
    finally:
        conn.close()
