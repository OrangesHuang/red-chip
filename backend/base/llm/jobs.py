"""LLM 分析任务管理: 后台线程执行 ReAct 循环, 前端轮询进度。

任务存内存(重启丢失, 可接受); 每个任务独占一个 daemon 线程。
"""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime

from base.llm.agent import run_analysis
from base.store.analysis_repo import save_report
from base.store.session_repo import append_message

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def start_job(
    code: str,
    name: str = "",
    history: list[dict] | None = None,
    session_id: str | None = None,
    user_prompt: str | None = None,
) -> str:
    """启动分析任务(支持多轮会话: 携带前序问答历史), 返回 job_id。"""
    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "code": code,
            "name": name,
            "status": "running",
            "steps": [],
            "result": None,
            "error": None,
            "usage": None,
            "session_id": session_id,
            "created_at": _now(),
        }
    threading.Thread(target=_run, args=(job_id, code, history, session_id, user_prompt), daemon=True).start()
    return job_id


def _run(
    job_id: str,
    code: str,
    history: list[dict] | None = None,
    session_id: str | None = None,
    user_prompt: str | None = None,
) -> None:
    def on_step(kind: str, message: str, detail: str | None = None, update: bool = False) -> None:
        nonlocal prev_ts
        now = time.time()
        duration = round(now - prev_ts, 1)
        prev_ts = now
        with _lock:
            job = _jobs.get(job_id)
            if not job:
                return
            if update and job["steps"]:
                last = job["steps"][-1]
                last.update(message=message, detail=detail, time=_now(), duration=duration)
            else:
                job["steps"].append(
                    {"kind": kind, "message": message, "detail": detail, "time": _now(), "duration": duration}
                )

    usage_acc: dict = {}
    try:
        prev_ts = time.time()
        on_step("start", "分析任务已启动, 正在请求 DeepSeek…")
        report = run_analysis(code, on_step=on_step, history=history, usage_acc=usage_acc, user_prompt=user_prompt)
        with _lock:
            job = _jobs.get(job_id)
            if job:
                job.update(status="done", result=report, usage=usage_acc or None)
        if session_id:
            append_message(session_id, "assistant", report, usage=usage_acc or None)
    except Exception as e:  # noqa: BLE001
        print(f"[LLM] analysis job {job_id} failed: {e}")
        with _lock:
            job = _jobs.get(job_id)
            if job:
                job.update(status="error", error=str(e), usage=usage_acc or None)
        if session_id:
            append_message(session_id, "assistant", f"⚠️ 分析失败: {e}", usage=usage_acc or None)
    with _lock:
        job = _jobs.get(job_id)
        if job:
            try:
                save_report(job)  # 持久化(完成/失败均入库)
            except Exception as e2:  # noqa: BLE001
                print(f"[LLM] save report {job_id} failed: {e2}")


def get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def list_jobs(limit: int = 10) -> list[dict]:
    with _lock:
        jobs = sorted(_jobs.values(), key=lambda j: j["created_at"], reverse=True)
        return [dict(j) for j in jobs[:limit]]
