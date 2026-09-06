"""analysis_report 表仓储: AI 分析报告持久化(任务完成后落库)。"""

from __future__ import annotations

import json

from base.store.database import get_connection


def save_report(job: dict) -> None:
    """保存任务记录(完成或失败都存, 便于追溯)。"""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO analysis_report
                (job_id, code, name, status, report, steps, error, created_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(job_id) DO UPDATE SET
                status=excluded.status, report=excluded.report, steps=excluded.steps,
                error=excluded.error, finished_at=datetime('now','localtime')
            """,
            (
                job.get("id"),
                job.get("code"),
                job.get("name"),
                job.get("status"),
                job.get("result"),
                json.dumps(job.get("steps") or [], ensure_ascii=False),
                job.get("error"),
                job.get("created_at"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_reports(code: str | None = None, limit: int = 20) -> list[dict]:
    """报告列表(不含全文, 只含摘要), 按完成时间倒序。"""
    conn = get_connection()
    try:
        if code:
            cur = conn.execute(
                """
                SELECT job_id, code, name, status, created_at, finished_at,
                       length(report) AS report_len
                FROM analysis_report WHERE code = ?
                ORDER BY finished_at DESC LIMIT ?
                """,
                (code, limit),
            )
        else:
            cur = conn.execute(
                """
                SELECT job_id, code, name, status, created_at, finished_at,
                       length(report) AS report_len
                FROM analysis_report
                ORDER BY finished_at DESC LIMIT ?
                """,
                (limit,),
            )
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return rows


def get_report(job_id: str) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM analysis_report WHERE job_id = ?",
            (job_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
