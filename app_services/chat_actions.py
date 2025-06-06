from fastapi import APIRouter, Depends, HTTPException, status, Query
from app_services.app_service_server import AppserviceServerInstance
from models_v_0_0_1 import (
    ChatActionRequest,
    ChatActionResponse,
    CheckSessionResponse,
    FetchChatHistoryResponse,
)
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph_services.langgraph_request_task import (
    LanggraphRequestTask,
)
from typing import cast
from app_services.oauth_user import get_authenticated_user
import db.redis_user_session
import db.redis_user
import app_services.user_session
import prompt.builtin as builtin_prompt
from langgraph_services.langgraph_models import (
    RequestTaskMessageType,
)


# 测试健康检查。
# services_health = (
#     await appservice_server.langgraph_service.check_services_health()
# )

# 测试。
# if request_data.content != "":
#     return ChatActionResponse(
#         message=f"收到: {request_data.content}",
#     )

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

        if len(request_data.content.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请求内容不能为空",
            )

        display_name = db.redis_user.get_user_display_name(username=authenticated_user)
        assert (
            display_name != ""
        ), f"用户 {authenticated_user} 的显示名称不能为空，请先设置显示名称。"
        current_user_session = (
            app_services.user_session.retrieve_or_initialize_user_session(
                authenticated_user
            )
        )

        prompt = builtin_prompt.user_session_chat_message(
            username=authenticated_user,
            display_name=display_name,
            content=request_data.content,
        )

        # 组织请求
        system_messages = [
            SystemMessage(
                content=builtin_prompt.user_session_system_message(
                    authenticated_user,
                    display_name,
                )
            ),
        ]

        request_task = LanggraphRequestTask(
            username=authenticated_user,
            prompt=prompt,
            chat_history=cast(
                RequestTaskMessageType,
                system_messages + current_user_session.chat_history,
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

        # 更新用户会话到 Redis
        db.redis_user_session.append_messages_to_session(
            user_session=current_user_session,
            new_messages=messages,
        )

        # 打印聊天记录
        for msg in system_messages + current_user_session.chat_history:
            logger.warning(msg.content)

        # 返回响应
        return ChatActionResponse(
            message=request_task.last_response_message_content,
            highest_sequence=len(current_user_session.chat_history),
        )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@chat_action_router.get(
    path="/action/fetch_chat_history/v1/", response_model=FetchChatHistoryResponse
)
async def handle_fetch_chat_history(
    index: int = Query(0, ge=0, description="获取历史记录的起始索引"),
    length: int = Query(10, gt=0, le=100, description="要获取的消息数量"),
    authenticated_user: str = Depends(get_authenticated_user),
) -> FetchChatHistoryResponse:
    """
    获取用户聊天历史的指定范围内容

    参数:
    - index: 起始索引，从0开始
    - length: 要获取的消息数量，最大100条
    """
    logger.info(f"/action/fetch_chat_history/v1/: index={index}, length={length}")

    try:
        # 获取用户会话
        current_user_session = (
            app_services.user_session.retrieve_or_initialize_user_session(
                authenticated_user
            )
        )

        # 获取聊天历史总长度
        total_count = len(current_user_session.chat_history)

        # 检查索引是否有效
        if index >= total_count:
            # 索引超出范围，返回空结果
            return FetchChatHistoryResponse(
                messages=[], total_count=total_count, has_more=False
            )

        # 计算实际结束索引（考虑边界）
        end_index = min(index + length, total_count)

        # 获取指定范围的消息
        messages_slice = current_user_session.chat_history[index:end_index]

        # 构建响应
        return FetchChatHistoryResponse(
            messages=messages_slice,
            total_count=total_count,
            has_more=(end_index < total_count),
        )

    except Exception as e:
        logger.error(f"获取聊天历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取聊天历史失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@chat_action_router.get(
    path="/action/check_session/v1/", response_model=CheckSessionResponse
)
async def handle_check_session(
    authenticated_user: str = Depends(get_authenticated_user),
) -> CheckSessionResponse:
    logger.info(f"/action/check_session/v1/: {authenticated_user}")
    try:
        # 获取用户会话
        current_user_session = (
            app_services.user_session.retrieve_or_initialize_user_session(
                authenticated_user
            )
        )

        # 返回会话的最高序列号
        return CheckSessionResponse(
            highest_sequence=len(current_user_session.chat_history),
        )

    except Exception as e:
        logger.error(f"检查会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查会话失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
