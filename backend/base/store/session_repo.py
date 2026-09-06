"""analysis_session 表仓储: AI 多轮会话(消息 JSON 存储)。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from base.store.database import get_connection


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_session(code: str, name: str | None = None) -> str:
    sid = uuid.uuid4().hex[:12]
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO analysis_session (id, code, name, messages, created_at, updated_at) VALUES (?, ?, ?, '[]', ?, ?)",
            (sid, code, name, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return sid


def get_session(session_id: str) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM analysis_session WHERE id = ?", (session_id,))
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        try:
            result["messages"] = json.loads(result.get("messages") or "[]")
        except ValueError:
            result["messages"] = []
        return result
    finally:
        conn.close()


def list_sessions(code: str | None = None, limit: int = 20) -> list[dict]:
    conn = get_connection()
    try:
        if code:
            cur = conn.execute(
                "SELECT id, code, name, messages, created_at, updated_at FROM analysis_session "
                "WHERE code = ? ORDER BY updated_at DESC LIMIT ?",
                (code, limit),
            )
        else:
            cur = conn.execute(
                "SELECT id, code, name, messages, created_at, updated_at FROM analysis_session "
                "ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
        rows = []
        for r in cur.fetchall():
            item = dict(r)
            try:
                msgs = json.loads(item.get("messages") or "[]")
            except ValueError:
                msgs = []
            item["message_count"] = len(msgs)
            item.pop("messages", None)
            rows.append(item)
        return rows
    finally:
        conn.close()


def append_message(session_id: str, role: str, content: str, usage: dict | None = None) -> bool:
    """追加一条消息(读-改-写, 任务线程与查询线程并发安全由 SQLite 锁保证)。"""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT messages FROM analysis_session WHERE id = ?", (session_id,))
        row = cur.fetchone()
        if not row:
            return False
        try:
            msgs = json.loads(row["messages"] or "[]")
        except ValueError:
            msgs = []
        msgs.append(
            {
                "role": role,
                "content": content,
                "usage": usage or {},
                "time": _now(),
            }
        )
        conn.execute(
            "UPDATE analysis_session SET messages = ?, updated_at = ? WHERE id = ?",
            (json.dumps(msgs, ensure_ascii=False), _now(), session_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()
