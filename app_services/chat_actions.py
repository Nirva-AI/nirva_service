from fastapi import APIRouter, Depends, HTTPException, status
from app_services.app_service_server import AppserviceServerInstance
from models_v_0_0_1 import (
    ChatActionRequest,
    ChatActionResponse,
)
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage
from langgraph_services.langgraph_request_task import (
    LanggraphRequestTask,
)
from typing import cast
from app_services.oauth_user import get_authenticated_user
import db.redis_user_session

# import db.pgsql_user_session
import db.redis_user
import app_services.user_session
import prompt.builtin as builtin_prompt
from langgraph_services.langgraph_models import (
    RequestTaskMessageType,
)

###################################################################################################################################################################
chat_action_router = APIRouter()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@chat_action_router.post(path="/action/chat/v1/", response_model=ChatActionResponse)
async def handle_chat_action(
    request_data: ChatActionRequest,
    appservice_server: AppserviceServerInstance,
    authenticated_user: str = Depends(get_authenticated_user),
) -> ChatActionResponse:

    logger.info(f"/action/chat/v1/: {request_data.model_dump_json()}")

    try:

        # 测试健康检查。
        # services_health = (
        #     await appservice_server.langgraph_service.check_services_health()
        # )

        # 测试。
        # if request_data.content != "":
        #     return ChatActionResponse(
        #         message=f"收到: {request_data.content}",
        #     )

        display_name = db.redis_user.get_user_display_name(username=authenticated_user)
        assert (
            display_name != ""
        ), f"用户 {authenticated_user} 的显示名称不能为空，请先设置显示名称。"
        current_user_session = app_services.user_session.get_or_create_user_session(
            authenticated_user, display_name
        )

        prompt = builtin_prompt.user_session_chat_message(
            username=authenticated_user,
            display_name=display_name,
            content=request_data.content,
        )

        # 组织请求
        request_task = LanggraphRequestTask(
            username=authenticated_user,
            prompt=prompt,
            chat_history=cast(
                RequestTaskMessageType,
                current_user_session.chat_history,
            ),
        )

        # 处理请求
        appservice_server.langgraph_service.chat(request_handlers=[request_task])
        if len(request_task._response.messages) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="处理请求时未返回内容",
            )

        # 准备添加消息
        messages = [
            HumanMessage(content=prompt),
            AIMessage(content=request_task.last_response_message_content),
        ]

        # 将消息添加到会话中
        current_user_session.chat_history.extend(messages)

        # 更新用户会话到 Redis 和 PostgreSQL
        db.redis_user_session.append_messages_to_session(
            user_session=current_user_session,
            new_messages=messages,
        )

        # 打印聊天记录
        for msg in current_user_session.chat_history:
            logger.info(msg.content)

        # 返回响应
        return ChatActionResponse(
            message=request_task.last_response_message_content,
        )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
