from fastapi import APIRouter, Depends, HTTPException, status
from app_services.app_service_server import AppserviceServerInstance
from models_v_0_0_1 import (
    AnalyzeActionRequest,
    AnalyzeActionResponse,
)
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph_services.langgraph_request_task import LanggraphRequestTask
from typing import List, cast
from app_services.oauth_user import get_authenticated_user
import db.redis_user_session
import db.pgsql_user_session
import db.redis_user

##import user_services.user_session
import prompt.builtin as builtin_prompt

###################################################################################################################################################################
analyze_action_router = APIRouter()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@analyze_action_router.post(
    path="/action/analyze/v1/", response_model=AnalyzeActionResponse
)
async def handle_chat_action(
    request_data: AnalyzeActionRequest,
    user_session_server: AppserviceServerInstance,
    authenticated_user: str = Depends(get_authenticated_user),
) -> AnalyzeActionResponse:

    logger.info(f"/action/analyze/v1/: {request_data.model_dump_json()}")

    try:

        # if request_data.content != "":
        return AnalyzeActionResponse(
            message=f"收到: {request_data.content} !!!!!!",
        )

        # display_name = db.redis_user.get_user_display_name(username=authenticated_user)
        # assert (
        #     display_name != ""
        # ), f"用户 {authenticated_user} 的显示名称不能为空，请先设置显示名称。"
        # current_user_session = user_services.user_session.get_or_create_user_session(
        #     authenticated_user, display_name
        # )

        # prompt = builtin_prompt.user_session_chat_message(
        #     username=authenticated_user,
        #     display_name=display_name,
        #     content=request_data.content,
        # )

        # # 组织请求
        # chat_request_handler = LanggraphRequestTask(
        #     username=authenticated_user,
        #     prompt=prompt,
        #     chat_history=cast(
        #         List[SystemMessage | HumanMessage | AIMessage],
        #         current_user_session.chat_history,
        #     ),
        # )

        # # 处理请求
        # user_session_server.langgraph_service.chat(
        #     request_handlers=[chat_request_handler]
        # )
        # if chat_request_handler.response_output == "":
        #     raise HTTPException(
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #         detail="处理请求时未返回内容",
        #     )

        # # 准备添加消息
        # messages = [
        #     HumanMessage(content=prompt),
        #     AIMessage(content=chat_request_handler.response_output),
        # ]

        # # 将消息添加到会话中
        # current_user_session.chat_history.extend(messages)

        # # 更新用户会话到 Redis 和 PostgreSQL
        # db.redis_user_session.update_user_session(
        #     user_session=current_user_session,
        #     new_messages=messages,
        # )

        # db.pgsql_user_session.update_user_session(
        #     user_session=current_user_session,
        #     new_messages=messages,
        # )

        # # 打印聊天记录
        # for msg in current_user_session.chat_history:
        #     logger.warning(msg.content)

        # # 返回响应
        # return ChatActionResponse(
        #     message=chat_request_handler.response_output,
        # )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
