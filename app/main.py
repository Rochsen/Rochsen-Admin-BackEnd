import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from uvicorn import run

from app.auth.views import router as auth_router
from app.core import lifespan
from app.core.config import get_settings
from app.probe.views import router as probe_router
from app.user.views import router as user_router

logger = logging.getLogger(__name__)


app = FastAPI(
    title="个人管理系统",
    version="8.0.0",
    description="https://github.com/Rochsen/Rochsen-Admin-BackEnd",
    openapi_url="/openapi.json",
    docs_url="/",
    lifespan=lifespan.lifespan,
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(probe_router, prefix="/probe", tags=["probe"])

# 设置所有启用 CORS 的来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        str(origin).rstrip("/")
        for origin in get_settings().security.backend_cors_origins
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 防护 HTTP 主机头攻击
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=get_settings().security.allowed_hosts,
)


if __name__ == "__main__":
    run("app.main:app", host="0.0.0.0", port=8864, reload=True)
