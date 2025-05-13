from fastapi import APIRouter
from services.user_session_server_instance import UserSessionServerInstance
from models_v_0_0_1 import (
    ChatActionRequest,
    ChatActionResponse,
)
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage
from llm_serves.chat_service_request_handler import ChatServiceRequestHandler

###################################################################################################################################################################
chat_action_router = APIRouter()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@chat_action_router.post(path="/action/chat/v1/", response_model=ChatActionResponse)
async def handle_chat_action(
    request_data: ChatActionRequest,
    user_session_server: UserSessionServerInstance,
) -> ChatActionResponse:

    logger.info(f"/action/chat/v1/: {request_data.model_dump_json()}")

    user_session_manager = user_session_server.user_session_manager
    if not user_session_manager.has_user_session(request_data.user_name):
        logger.error(
            f"action/chat/v1: {request_data.user_name} has no session, please login first."
        )
        return ChatActionResponse(
            error=1001,
            message="没有登录，请先登录",
        )

    current_user_session = user_session_manager.get_user_session(request_data.user_name)
    assert current_user_session is not None

    # 在这里写一个等待，故意等一会
    # import time
    # time.sleep(5)
    # return ChatActionResponse(
    #     error=0,
    #     message=request_data.content,
    # )

    try:

        # 组织请求
        chat_request_handler = ChatServiceRequestHandler(
            user_name=request_data.user_name,
            prompt=request_data.content,
            chat_history=current_user_session.chat_history,
        )

        # 处理请求
        user_session_manager.chat_service_request_manager.handle(
            request_handlers=[chat_request_handler]
        )

        # 处理返回添加上下文。
        current_user_session.chat_history.append(
            HumanMessage(content=request_data.content)
        )
        current_user_session.chat_history.append(
            AIMessage(content=chat_request_handler.response_content)
        )

        # 打印聊天记录
        for msg in current_user_session.chat_history:
            logger.warning(msg.content)

        return ChatActionResponse(
            error=0,
            message=chat_request_handler.response_content,
        )

    except Exception as e:
        return ChatActionResponse(
            error=1002,
            message=f"处理请求失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
