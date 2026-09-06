"""AI 分析 API: LLM 设置 / 启动分析任务 / 进度轮询 / 连接测试。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from base.config import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL
from base.llm.client import LLMError, chat_completion
from base.llm.jobs import get_job, list_jobs, start_job
from base.pool import get_stock
from base.store.analysis_repo import get_report, list_reports
from base.store.session_repo import append_message, create_session, get_session, list_sessions
from base.store.settings_repo import get_setting, set_setting

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class SettingsBody(BaseModel):
    api_key: str | None = None  # 留空表示不修改
    model: str | None = None
    base_url: str | None = None


class SessionCreateBody(BaseModel):
    code: str


class MessageBody(BaseModel):
    content: str


def _mask_key(key: str | None) -> str:
    if not key:
        return ""
    return f"{key[:4]}****{key[-4:]}" if len(key) > 8 else "****"


@router.get("/settings")
def analysis_settings():
    key = get_setting("llm_api_key") or ""
    return {
        "configured": bool(key),
        "key_masked": _mask_key(key),
        "model": get_setting("llm_model") or DEFAULT_LLM_MODEL,
        "base_url": get_setting("llm_base_url") or DEFAULT_LLM_BASE_URL,
    }


@router.put("/settings")
def update_settings(body: SettingsBody):
    if body.api_key is not None and body.api_key.strip():
        set_setting("llm_api_key", body.api_key.strip())
    if body.model is not None and body.model.strip():
        set_setting("llm_model", body.model.strip())
    if body.base_url is not None and body.base_url.strip():
        set_setting("llm_base_url", body.base_url.strip().rstrip("/"))
    return analysis_settings()


@router.post("/test")
def test_connection(body: SettingsBody | None = None):
    """用当前配置(或请求内临时 key)发一条最小请求验证连通性。"""
    try:
        reply = chat_completion(
            [
                {"role": "system", "content": "你是连通性测试助手, 回复 JSON。"},
                {"role": "user", "content": '请回复 {"ok": true}'},
            ],
            api_key=body.api_key if body else None,
            model=body.model if body else None,
            base_url=body.base_url if body else None,
        )
        return {"ok": True, "reply": reply[:200]}
    except LLMError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


@router.post("/stock/{code}")
def start_stock_analysis(code: str):
    """启动个股 AI 分析任务(后台线程, 前端轮询进度)。"""
    info = get_stock(code)
    if info is None:
        raise HTTPException(status_code=404, detail=f"unknown stock code: {code}")
    job_id = start_job(code, name=info.get("name", code))
    return {"job_id": job_id, "code": code}


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"unknown job: {job_id}")
    return job


@router.get("/jobs")
def jobs(limit: int = 10):
    return {"jobs": list_jobs(limit)}


# ─── 多轮会话 ─────────────────────────────────────────────────────


def _history_from_session(session: dict) -> list[dict]:
    """会话消息 → 模型历史(仅保留 user 提问与 assistant 报告, 不含工具内部细节)。"""
    history: list[dict] = []
    for m in session.get("messages") or []:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})
    return history


@router.post("/sessions")
def create_analysis_session(body: SessionCreateBody):
    """创建多轮分析会话(消息持久化到 SQLite)。"""
    info = get_stock(body.code)
    if info is None:
        raise HTTPException(status_code=404, detail=f"unknown stock code: {body.code}")
    session_id = create_session(body.code, name=info.get("name", body.code))
    return {"session_id": session_id, "code": body.code, "name": info.get("name")}


@router.get("/sessions")
def sessions(code: str | None = None, limit: int = 20):
    """会话列表(按更新时间倒序)。"""
    return {"sessions": list_sessions(code=code, limit=limit)}


@router.get("/sessions/{session_id}")
def session_detail(session_id: str):
    """会话详情: 完整消息历史。"""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"unknown session: {session_id}")
    return session


@router.post("/sessions/{session_id}/messages")
def send_message(session_id: str, body: MessageBody):
    """发送提问(含补充提示词), 追加为会话消息并启动分析回合。"""
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"unknown session: {session_id}")
    append_message(session_id, "user", content)
    history = _history_from_session(session)
    job_id = start_job(
        session["code"],
        name=session.get("name") or session["code"],
        history=history,
        session_id=session_id,
        user_prompt=content,  # 本轮真实提问(此前被通用提示词替代, 导致每次回答雷同)
    )
    return {"job_id": job_id, "session_id": session_id}


@router.get("/reports")
def reports(code: str | None = None, limit: int = 20):
    """历史分析报告列表(摘要, 不含全文), 按完成时间倒序。"""
    return {"reports": list_reports(code=code, limit=limit)}


@router.get("/reports/{job_id}")
def report_detail(job_id: str):
    """历史分析报告全文 + 步骤日志。"""
    report = get_report(job_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"unknown report: {job_id}")
    if report.get("steps"):
        try:
            import json

            report["steps"] = json.loads(report["steps"])
        except ValueError:
            report["steps"] = []
    return report
