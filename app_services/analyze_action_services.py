import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app_services.app_service_server import AppserviceServerInstance
from models_v_0_0_1 import (
    AnalyzeActionRequest,
    AnalyzeActionResponse,
)
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph_services.langgraph_request_task import LanggraphRequestTask
from typing import List, Tuple, cast, Optional
from app_services.oauth_user import get_authenticated_user
import db.redis_user
import prompt.builtin as builtin_prompt
from prompt.builtin import LabelExtractionResponse, ReflectionResponse
import utils.format_string as format_string
import json


class MyDump(BaseModel):
    messages: List[BaseMessage]


###################################################################################################################################################################
def execute_label_extraction(
    authenticated_user: str,
    chat_history: List[SystemMessage | HumanMessage | AIMessage],
    user_session_server: AppserviceServerInstance,
) -> Tuple[
    Optional[LabelExtractionResponse], List[SystemMessage | HumanMessage | AIMessage]
]:
    """
    执行步骤1~2：标签提取过程

    Args:
        authenticated_user: 认证用户名
        chat_history: 当前聊天历史
        user_session_server: 用户会话服务器实例

    Returns:
        提取的标签响应对象和更新后的聊天历史
    """
    current_time_tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

    step1_2_request = LanggraphRequestTask(
        username=authenticated_user,
        prompt=builtin_prompt.label_extraction_message(),
        chat_history=chat_history,
        timeout=60,
    )

    # 处理请求
    user_session_server.langgraph_service.analyze(request_handlers=[step1_2_request])
    if step1_2_request.response_output == "":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="处理请求时未返回内容",
        )

    # 准备添加消息
    messages: List[SystemMessage | HumanMessage | AIMessage] = [
        HumanMessage(content=builtin_prompt.label_extraction_message()),
        AIMessage(content=step1_2_request.response_output),
    ]

    # 将消息添加到会话中
    chat_history.extend(messages)

    # 打印聊天记录
    # for msg in chat_history:
    #     logger.warning(msg.content)

    my_dump = MyDump(messages=cast(List[BaseMessage], chat_history))

    label_extraction_response_path = Path("logs") / f"dump1-2-{current_time_tag}.json"
    label_extraction_response_path.write_text(
        my_dump.model_dump_json(), encoding="utf-8"
    )
    logger.info("Dump written to:", label_extraction_response_path)

    json_content = format_string.extract_json_from_codeblock(
        step1_2_request.response_output
    )

    label_extraction_response = None
    if json_content:
        # 解析 JSON 内容
        try:
            label_extraction_response = LabelExtractionResponse.model_validate_json(
                json_content
            )
            logger.info("Label extraction response:", label_extraction_response)
            label_extraction_response_path = (
                Path("logs") / f"label_extraction_response-{current_time_tag}.json"
            )
            label_extraction_response_path.write_text(
                label_extraction_response.model_dump_json(),
                encoding="utf-8",
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
    else:
        logger.warning("No JSON content found in the last message.")

    return label_extraction_response, chat_history


###################################################################################################################################################################
def execute_reflection(
    authenticated_user: str,
    chat_history: List[SystemMessage | HumanMessage | AIMessage],
    user_session_server: AppserviceServerInstance,
) -> Tuple[
    Optional[ReflectionResponse], List[SystemMessage | HumanMessage | AIMessage]
]:
    """
    执行步骤3：反思过程

    Args:
        authenticated_user: 认证用户名
        chat_history: 当前聊天历史
        user_session_server: 用户会话服务器实例

    Returns:
        反思响应对象和更新后的聊天历史
    """
    current_time_tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

    step3_request = LanggraphRequestTask(
        username=authenticated_user,
        prompt=builtin_prompt.reflection_message(),
        chat_history=chat_history,
        timeout=60,
    )

    # 处理请求
    user_session_server.langgraph_service.analyze(request_handlers=[step3_request])
    if step3_request.response_output == "":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="处理请求时未返回内容",
        )

    # 准备添加消息
    messages: List[SystemMessage | HumanMessage | AIMessage] = [
        HumanMessage(content=builtin_prompt.reflection_message()),
        AIMessage(content=step3_request.response_output),
    ]

    # 将消息添加到会话中
    chat_history.extend(messages)

    my_dump = MyDump(messages=cast(List[BaseMessage], chat_history))

    # 保存dump文件
    dump3_path = Path("logs") / f"dump3-{current_time_tag}.json"
    dump3_path.write_text(my_dump.model_dump_json(), encoding="utf-8")
    logger.info("Dump written to:", dump3_path)

    json_content = format_string.extract_json_from_codeblock(
        step3_request.response_output
    )

    reflection_response = None
    if json_content:
        # 解析 JSON 内容
        try:
            reflection_response = ReflectionResponse.model_validate_json(json_content)
            logger.info("Reflection response:", reflection_response)
            reflection_response_path = (
                Path("logs") / f"reflection_response-{current_time_tag}.json"
            )
            reflection_response_path.write_text(
                reflection_response.model_dump_json(),
                encoding="utf-8",
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
    else:
        logger.warning("No JSON content found in the last message.")

    return reflection_response, chat_history


###################################################################################################################################################################
analyze_action_router = APIRouter()


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@analyze_action_router.post(
    path="/action/analyze/v1/", response_model=AnalyzeActionResponse
)
async def handle_analyze_action(
    request_data: AnalyzeActionRequest,
    user_session_server: AppserviceServerInstance,
    authenticated_user: str = Depends(get_authenticated_user),
) -> AnalyzeActionResponse:

    logger.info(f"/action/analyze/v1/: {request_data.model_dump_json()}")

    try:

        transcript_content = (
            request_data.content
        )  # invisible_path.read_text(encoding="utf-8").strip()
        assert transcript_content != "", "转录内容不能为空"
        if transcript_content == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="转录内容不能为空。",
            )

        display_name = db.redis_user.get_user_display_name(username=authenticated_user)
        assert (
            display_name != ""
        ), f"用户 {authenticated_user} 的显示名称不能为空，请先设置显示名称。"

        chat_history: List[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(
                content=builtin_prompt.user_session_system_message(
                    authenticated_user, display_name
                )
            ),
            HumanMessage(content=builtin_prompt.event_segmentation_message()),
            HumanMessage(
                content=builtin_prompt.transcript_message(
                    formatted_date=request_data.datetime,
                    transcript_content=transcript_content,
                )
            ),
        ]

        # 步骤1~2: 标签提取过程
        label_extraction_response, chat_history = execute_label_extraction(
            authenticated_user=authenticated_user,
            chat_history=chat_history,
            user_session_server=user_session_server,
        )

        # 步骤3: 反思过程
        if label_extraction_response:
            reflection_response, chat_history = execute_reflection(
                authenticated_user=authenticated_user,
                chat_history=chat_history,
                user_session_server=user_session_server,
            )

        return AnalyzeActionResponse(
            label_extraction=label_extraction_response,
            reflection=reflection_response,
            message="分析过程已完成",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################


# pm2 start run_analyzer_server.py
