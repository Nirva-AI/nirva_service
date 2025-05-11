from pathlib import Path
from typing import List
from fastapi import APIRouter
from config.configuration import LLMServerConfig
from services.user_session_server_instance import UserSessionServerInstance
from models_v_0_0_1 import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
)
from loguru import logger
from llm_serves.chat_request_manager import ChatRequestManager
from services.options import UserSessionOptions
from config.configuration import LLM_SERVER_CONFIG_PATH

###################################################################################################################################################################
login_router = APIRouter()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@login_router.post(path="/login/v1/", response_model=LoginResponse)
async def login(
    request_data: LoginRequest,
    user_session_server: UserSessionServerInstance,
) -> LoginResponse:

    logger.info(f"login/v1: {request_data.model_dump_json()}")

    user_session_manager = user_session_server.user_session_manager

    user_session_options = UserSessionOptions(
        user=request_data.user_name,
    )
    user_session_options.setup_logger()

    # 先检查会话是否存在
    if not user_session_manager.has_user_session(request_data.user_name):
        logger.info(f"login/v1: {request_data.user_name} not found, create session")
        new_user_session = user_session_manager.create_user_session(
            user_name=request_data.user_name,
        )
        logger.info(
            f"login/v1: {request_data.user_name} create session = {new_user_session._user_name}"
        )

        config_file_content = LLM_SERVER_CONFIG_PATH.read_text(encoding="utf-8")
        assert (
            LLM_SERVER_CONFIG_PATH.exists()
        ), f"找不到配置文件: {LLM_SERVER_CONFIG_PATH}"
        llm_server_config = LLMServerConfig.model_validate_json(config_file_content)
        localhost_urls: List[str] = [
            f"http://localhost:{llm_server_config.port}{llm_server_config.api}"
        ]

        # 创建ChatSystem
        new_user_session._chat_system = ChatRequestManager(
            # name=f"{request_data.user_name}-chatsystem",
            # user_name=request_data.user_name,
            localhost_urls=localhost_urls,
        )

    # 获取
    current_user_session = user_session_manager.get_user_session(request_data.user_name)
    assert current_user_session is not None

    #
    return LoginResponse(
        error=0,
        message=request_data.model_dump_json(),
    )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@login_router.post(path="/logout/v1/", response_model=LogoutResponse)
async def logout(
    request_data: LogoutRequest,
    user_session_server: UserSessionServerInstance,
) -> LogoutResponse:

    logger.info(f"/logout/v1/: {request_data.model_dump_json()}")

    # 先检查会话是否存在
    user_session_manager = user_session_server.user_session_manager
    if not user_session_manager.has_user_session(request_data.user_name):
        logger.error(f"logout: {request_data.user_name} not found")
        return LogoutResponse(
            error=1001,
            message="没有找到会话",
        )

    # 获取
    pre_user_session = user_session_manager.get_user_session(request_data.user_name)
    assert pre_user_session is not None
    user_session_manager.remove_user_session(pre_user_session)

    return LogoutResponse(
        error=0,
        message=request_data.model_dump_json(),
    )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
