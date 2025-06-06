from fastapi import APIRouter, Depends, HTTPException, status
from app_services.app_service_server import AppserviceServerInstance
from models_v_0_0_1 import (
    ChatActionRequest,
    ChatActionResponse,
)
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph_services.langgraph_request_task import (
    LanggraphRequestTask,
)
from typing import List, cast
from app_services.oauth_user import get_authenticated_user
import db.redis_user
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
def _assemble_chat_messages(
    messages_type: List[str], messages_content: List[str]
) -> RequestTaskMessageType:
    """
    根据消息类型和内容构建聊天历史消息列表。
    """
    assert len(messages_type) == len(messages_content), "消息类型和内容长度不匹配。"

    ret_messages: RequestTaskMessageType = []
    for message_type, message_content in zip(messages_type, messages_content):
        if message_type == "system":
            ret_messages.append(SystemMessage(content=message_content))
        elif message_type == "human":
            ret_messages.append(HumanMessage(content=message_content))
        elif message_type == "ai":
            ret_messages.append(AIMessage(content=message_content))
        else:
            logger.warning(f"Unknown message type: {message_type}")
            raise ValueError(f"Unknown message type: {message_type}")

    return ret_messages


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

        chat_history = _assemble_chat_messages(
            messages_type=request_data.chat_history_types,
            messages_content=request_data.chat_history_contents,
        )

        request_task = LanggraphRequestTask(
            username=authenticated_user,
            prompt=prompt,
            chat_history=cast(
                RequestTaskMessageType,
                system_messages + chat_history,
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
        messages: RequestTaskMessageType = [
            HumanMessage(content=prompt),
            AIMessage(content=request_task.last_response_message_content),
        ]

        # 将消息添加到会话中
        chat_history.extend(messages)

        # 打印聊天记录
        for msg in system_messages + chat_history:
            logger.warning(msg.content)

        # 返回响应
        return ChatActionResponse(
            human_message_content=prompt,
            ai_response_content=request_task.last_response_message_content,
        )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
