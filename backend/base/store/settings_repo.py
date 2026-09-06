"""设置表仓储(key-value)。"""

from __future__ import annotations

from base.store.database import get_connection


def get_setting(key: str) -> str | None:
    conn = get_connection()
    try:
        cur = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now','localtime'))
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now','localtime')
            """,
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()
