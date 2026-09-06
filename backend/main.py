"""App 组装入口: 路由注册 + CORS + 前端静态托管(生产)。仅组装, 无业务逻辑。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.analysis import router as analysis_router
from api.data import router as data_router
from base.api.static import mount_frontend
from base.scheduler.tasks import start_scheduler, stop_scheduler
from base.store.database import init_db
from dividend.api import router as dividend_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="红筹高股息因子分析", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5190", "http://127.0.0.1:5190"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for router in (dividend_router, data_router, analysis_router):
    app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


mount_frontend(app)
