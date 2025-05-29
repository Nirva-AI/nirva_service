from fastapi import APIRouter
from user_services.user_session_server_instance import UserSessionServerInstance
from models_v_0_0_1 import (
    ChatActionRequest,
    ChatActionResponse,
)
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from llm_services.chat_service_request_handler import ChatServiceRequestHandler
from typing import List, cast

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

    current_user_session = user_session_server.user_sessions.acquire_user_session(
        request_data.user_name
    )

    try:

        # 组织请求
        chat_request_handler = ChatServiceRequestHandler(
            user_name=request_data.user_name,
            prompt=request_data.content,
            chat_history=cast(
                List[SystemMessage | HumanMessage | AIMessage],
                current_user_session.chat_history,
            ),
        )

        # 处理请求
        user_session_server.chat_service.handle(request_handlers=[chat_request_handler])

        if chat_request_handler.response_content != "":

            human_message = HumanMessage(content=request_data.content)
            ai_message = AIMessage(content=chat_request_handler.response_content)

            current_user_session.chat_history.extend(
                [
                    human_message,
                    ai_message,
                ]
            )

            user_session_server.user_sessions.update_user_session_with_new_messages(
                user_session=current_user_session,
                messages=[
                    human_message,
                    ai_message,
                ],
            )

            # 打印聊天记录
            for msg in current_user_session.chat_history:
                logger.warning(msg.content)

            # 返回响应
            return ChatActionResponse(
                error=0,
                message=chat_request_handler.response_content,
            )

    except Exception as e:
        return ChatActionResponse(
            error=1002,
            message=f"处理请求失败: {e}",
        )

    return ChatActionResponse(
        error=1003,
        message="处理请求失败: 未知错误",
    )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
