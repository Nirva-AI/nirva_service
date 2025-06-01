from fastapi import APIRouter, Depends, HTTPException, status
from user_services.user_session_server import UserSessionServerInstance
from models_v_0_0_1 import (
    ChatActionRequest,
    ChatActionResponse,
)
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from llm_services.chat_service_request_handler import ChatServiceRequestHandler
from typing import List, cast
from user_services.oauth_user import get_authenticated_user
import db.redis_user_session
import db.pgsql_user_session
import user_services.user_session
import prompt.builtin as builtin_prompt

###################################################################################################################################################################
chat_action_router = APIRouter()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@chat_action_router.post(path="/action/chat/v1/", response_model=ChatActionResponse)
async def handle_chat_action(
    request_data: ChatActionRequest,
    user_session_server: UserSessionServerInstance,
    authenticated_user: str = Depends(get_authenticated_user),
) -> ChatActionResponse:

    logger.info(f"/action/chat/v1/: {request_data.model_dump_json()}")

    try:

        if request_data.content != "":
            return ChatActionResponse(
                message=f"收到: {request_data.content}",
            )

        current_user_session = user_services.user_session.get_or_create_user_session(
            authenticated_user
        )

        # 组织请求
        chat_request_handler = ChatServiceRequestHandler(
            username=authenticated_user,
            prompt=builtin_prompt.user_session_chat_message(
                username=authenticated_user,
                display_name="",
                content=request_data.content,
            ),
            chat_history=cast(
                List[SystemMessage | HumanMessage | AIMessage],
                current_user_session.chat_history,
            ),
        )

        # 处理请求
        user_session_server.chat_service.handle(request_handlers=[chat_request_handler])
        if chat_request_handler.response_output == "":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="处理请求时未返回内容",
            )

        # 准备添加消息
        messages = [
            HumanMessage(content=request_data.content),
            AIMessage(content=chat_request_handler.response_output),
        ]

        # 将消息添加到会话中
        current_user_session.chat_history.extend(messages)

        # 更新用户会话到 Redis 和 PostgreSQL
        db.redis_user_session.update_user_session(
            user_session=current_user_session,
            new_messages=messages,
        )

        db.pgsql_user_session.update_user_session(
            user_session=current_user_session,
            new_messages=messages,
        )

        # 打印聊天记录
        for msg in current_user_session.chat_history:
            logger.warning(msg.content)

        # 返回响应
        return ChatActionResponse(
            message=chat_request_handler.response_output,
        )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
