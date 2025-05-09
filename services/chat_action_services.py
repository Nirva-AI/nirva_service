from fastapi import APIRouter
from services.user_session_server_instance import UserSessionServerInstance
from models_v_0_0_1 import (
    ChatActionRequest,
    ChatActionResponse,
)
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage
from llm_serves.chat_request_handler import ChatRequestHandler

###################################################################################################################################################################
chat_action_router = APIRouter()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@chat_action_router.post(path="/chat-action/v1/", response_model=ChatActionResponse)
async def handle_chat_action(
    request_data: ChatActionRequest,
    user_session_server: UserSessionServerInstance,
) -> ChatActionResponse:

    logger.info(f"/chat-action/v1/: {request_data.model_dump_json()}")

    user_session_manager = user_session_server.user_session_manager
    if not user_session_manager.has_user_session(request_data.user_name):
        logger.error(
            f"hchat-action/v1: {request_data.user_name} has no session, please login first."
        )
        return ChatActionResponse(
            error=1001,
            message="没有登录，请先登录",
        )

    current_user_session = user_session_manager.get_user_session(request_data.user_name)
    assert current_user_session is not None
    if current_user_session.chat_system is None:
        logger.error(
            f"chat-action/v1: {request_data.user_name} has no chat_system, please login first."
        )
        return ChatActionResponse(
            error=1002,
            message="没有游戏，请先登录",
        )

    try:
        chat_request_handler = ChatRequestHandler(
            name=request_data.user_name,
            prompt=request_data.content,
            chat_history=current_user_session.chat_history,
        )
        current_user_session.chat_system.handle(request_handlers=[chat_request_handler])
        current_user_session.chat_history.append(
            HumanMessage(content=request_data.content)
        )
        current_user_session.chat_history.append(
            AIMessage(content=chat_request_handler.response_content)
        )

        for msg in current_user_session.chat_history:
            logger.warning(msg.content)

        return ChatActionResponse(
            error=0,
            message=chat_request_handler.response_content,
        )

    except Exception as e:
        logger.error(f"Exception: {e}")

    return ChatActionResponse(
        error=1000,
        message="未知的请求类型, 不能处理！",
    )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
