from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...db.redis_client import get_redis
from .analyze_actions import analyze_action_router
from .audio_download import audio_download_router
from .chat_actions import chat_action_router
from .enhanced_chat_actions import enhanced_chat_router
from .voice_chat_actions import voice_chat_router
from .login import login_router
from .url_config import url_config_router
from .upload_auth import upload_auth_router
from .transcription_query import transcription_router
from ...routers.mental_state import router as mental_state_router


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
app.include_router(router=enhanced_chat_router)  # Enhanced chat with persistence
app.include_router(router=voice_chat_router)  # Voice message and call endpoints
app.include_router(router=analyze_action_router)
app.include_router(router=upload_auth_router)
app.include_router(router=transcription_router)
app.include_router(router=audio_download_router)
app.include_router(router=mental_state_router)
