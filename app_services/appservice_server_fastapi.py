from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from app_services.url_config import url_config_router
from app_services.login import login_router
from app_services.chat_actions import chat_action_router
from app_services.analyze_actions import analyze_action_router
from db.redis_client import get_redis
from collections.abc import AsyncGenerator


# redis!
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # 启动时连接
    app.state.redis = get_redis()
    yield
    # 关闭时清理
    app.state.redis.close()


# 初始化 FastAPI 应用
app = FastAPI(lifespan=lifespan)

#
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=url_config_router)
app.include_router(router=login_router)
app.include_router(router=chat_action_router)
app.include_router(router=analyze_action_router)
