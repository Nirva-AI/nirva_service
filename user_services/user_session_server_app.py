from fastapi.middleware.cors import CORSMiddleware
from user_services.user_session_server_instance import (
    initialize_user_session_server_instance,
)
from fastapi import FastAPI
from user_services.url_config_services import url_config_router
from user_services.login_services import login_router
from user_services.chat_action_services import chat_action_router

# singleton!
initialize_user_session_server_instance()

# 初始化 FastAPI 应用
app = FastAPI()

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
