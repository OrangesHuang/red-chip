"""factor_snapshot 表仓储: 因子快照(每股每日一版)。"""

from __future__ import annotations

from base.store.database import get_connection


def upsert_snapshot(snap: dict) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO factor_snapshot
                (date, code, close_price, change_pct, dps_ttm, div_yield, score,
                 grade, zone, odds, target_price, support_price, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(date, code) DO UPDATE SET
                close_price=excluded.close_price, change_pct=excluded.change_pct,
                dps_ttm=excluded.dps_ttm, div_yield=excluded.div_yield,
                score=excluded.score, grade=excluded.grade, zone=excluded.zone,
                odds=excluded.odds, target_price=excluded.target_price,
                support_price=excluded.support_price,
                updated_at=datetime('now','localtime')
            """,
            (
                snap.get("date"),
                snap.get("code"),
                snap.get("close_price"),
                snap.get("change_pct"),
                snap.get("dps_ttm"),
                snap.get("div_yield"),
                snap.get("score"),
                snap.get("grade"),
                snap.get("zone"),
                snap.get("odds"),
                snap.get("target_price"),
                snap.get("support_price"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def latest_snapshots(codes: list[str] | None = None) -> list[dict]:
    """每只股票最新一版快照(date DESC 每 code 首行)。codes 为空则全部。"""
    conn = get_connection()
    try:
        if codes:
            placeholders = ",".join("?" for _ in codes)
            cur = conn.execute(
                f"""
                SELECT s.date, s.code, s.close_price, s.change_pct, s.dps_ttm,
                       s.div_yield, s.score, s.grade, s.zone, s.odds,
                       s.target_price, s.support_price
                FROM factor_snapshot s
                JOIN (SELECT code, MAX(date) AS max_date FROM factor_snapshot
                      WHERE code IN ({placeholders}) GROUP BY code) m
                  ON s.code = m.code AND s.date = m.max_date
                ORDER BY s.score DESC
                """,
                codes,
            )
        else:
            cur = conn.execute(
                """
                SELECT s.date, s.code, s.close_price, s.change_pct, s.dps_ttm,
                       s.div_yield, s.score, s.grade, s.zone, s.odds,
                       s.target_price, s.support_price
                FROM factor_snapshot s
                JOIN (SELECT code, MAX(date) AS max_date FROM factor_snapshot GROUP BY code) m
                  ON s.code = m.code AND s.date = m.max_date
                ORDER BY s.score DESC
                """
            )
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return rows


def snapshot_dates(code: str, limit: int = 250) -> list[dict]:
    """某股票最近 limit 版快照(日期升序), 供历史曲线用。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT date, code, close_price, change_pct, dps_ttm, div_yield, score,
                   grade, zone, odds, target_price, support_price
            FROM factor_snapshot WHERE code = ?
            ORDER BY date DESC LIMIT ?
            """,
            (code, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    rows.reverse()
    return rows
