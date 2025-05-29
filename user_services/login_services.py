from fastapi import APIRouter
from user_services.user_session_server_instance import UserSessionServerInstance
from models_v_0_0_1 import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
)
from loguru import logger

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

    # 无所谓，直接发令牌就可以。
    logger.info(f"login/v1: {request_data.model_dump_json()}")
    return LoginResponse(
        error=0,
        message=request_data.model_dump_json(),
    )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
# "refresh": base + "refresh/v1/",
@login_router.post(path="/refresh/v1/", response_model=LoginResponse)
async def refresh(
    request_data: LoginRequest,
    user_session_server: UserSessionServerInstance,
) -> LoginResponse:
    # 无所谓，直接发令牌就可以。
    logger.info(f"refresh/v1: {request_data.model_dump_json()}")
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
    # 移除，关令牌。
    user_session_server.user_sessions.stop_user_session(request_data.user_name)
    return LogoutResponse(
        error=0,
        message=request_data.model_dump_json(),
    )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
