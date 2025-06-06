from fastapi import APIRouter, Depends, HTTPException, status
from app_services.app_service_server import AppserviceServerInstance
from models_v_0_0_1 import (
    AnalyzeActionRequest,
    AnalyzeActionResponse,
    UploadTranscriptActionRequest,
    UploadTranscriptActionResponse,
    LabelExtractionResponse,
    ReflectionResponse,
)
from loguru import logger
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph_services.langgraph_request_task import (
    LanggraphRequestTask,
)
from typing import List, Optional, cast
from app_services.oauth_user import get_authenticated_user
import db.redis_user
import prompt.builtin as builtin_prompt
import utils.format_string as format_string
from langgraph_services.langgraph_models import (
    RequestTaskMessageListType,
)
import time
import db.redis_upload_transcript


class AnalyzeProcessContext:

    def __init__(
        self,
        authenticated_user: str,
        chat_history: List[BaseMessage],
        appservice_server: AppserviceServerInstance,
    ):

        self._authenticated_user: str = authenticated_user
        self._chat_history: List[BaseMessage] = chat_history
        self._appservice_server: AppserviceServerInstance = appservice_server
        self._label_extraction_response: Optional[LabelExtractionResponse] = None
        self._reflection_response: Optional[ReflectionResponse] = None


###################################################################################################################################################################
def execute_label_extraction(
    analyze_process_context: AnalyzeProcessContext,
) -> None:

    try:

        # 构建 LanggraphRequestTask 请求
        step1_2_request = LanggraphRequestTask(
            username=analyze_process_context._authenticated_user,
            prompt=builtin_prompt.label_extraction_message(),
            chat_history=cast(
                RequestTaskMessageListType, analyze_process_context._chat_history
            ),
            timeout=60,
        )

        # 处理请求
        analyze_process_context._appservice_server.langgraph_service.analyze(
            request_handlers=[step1_2_request]
        )

        # 如果请求未返回内容，则抛出异常
        if len(step1_2_request._response.messages) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="处理请求时未返回内容",
            )

        json_content = format_string.extract_json_from_codeblock(
            step1_2_request.last_response_message_content
        )
        if json_content == "":
            logger.warning("No JSON content found in the last message.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="处理请求时未返回有效的 JSON 内容",
            )

        # 解析 JSON 内容
        analyze_process_context._label_extraction_response = (
            LabelExtractionResponse.model_validate_json(json_content)
        )

        # 新的消息。
        messages = [
            HumanMessage(content=builtin_prompt.label_extraction_message()),
            AIMessage(content=step1_2_request.last_response_message_content),
        ]

        # 将消息添加到会话中， 最后添加。
        analyze_process_context._chat_history.extend(messages)

        # 记录标签提取响应
        logger.info(
            "Label extraction response:",
            analyze_process_context._label_extraction_response.model_dump_json(),
        )

    except Exception as e:
        logger.error("Failed to execute label extraction:", e)
        raise e


###################################################################################################################################################################
def execute_reflection(
    analyze_process_context: AnalyzeProcessContext,
) -> None:

    try:

        # 构建 LanggraphRequestTask 请求
        step3_request = LanggraphRequestTask(
            username=analyze_process_context._authenticated_user,
            prompt=builtin_prompt.reflection_message(),
            chat_history=cast(
                RequestTaskMessageListType, analyze_process_context._chat_history
            ),
            timeout=60,
        )

        # 处理请求
        analyze_process_context._appservice_server.langgraph_service.analyze(
            request_handlers=[step3_request]
        )
        if len(step3_request._response.messages) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="处理请求时未返回内容",
            )

        json_content = format_string.extract_json_from_codeblock(
            step3_request.last_response_message_content
        )
        if json_content == "":
            logger.warning("No JSON content found in the last message.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="处理请求时未返回有效的 JSON 内容",
            )

        # 解析 JSON 内容
        analyze_process_context._reflection_response = (
            ReflectionResponse.model_validate_json(json_content)
        )

        # 新的消息。
        messages = [
            HumanMessage(content=builtin_prompt.reflection_message()),
            AIMessage(content=step3_request.last_response_message_content),
        ]

        # 将消息添加到会话中
        analyze_process_context._chat_history.extend(messages)

        # 记录反思响应
        logger.info(
            "Reflection response:",
            analyze_process_context._reflection_response.model_dump_json(),
        )

    except Exception as e:
        logger.error("Failed to execute reflection:", e)
        raise e


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
    appservice_server: AppserviceServerInstance,
    authenticated_user: str = Depends(get_authenticated_user),
) -> AnalyzeActionResponse:

    logger.info(f"/action/analyze/v1/: {request_data.model_dump_json()}")

    try:
        # 开始计时
        start_time = time.time()

        if not db.redis_upload_transcript.is_transcript_stored(
            username=authenticated_user,
            time_stamp=request_data.time_stamp,
            file_number=request_data.file_number,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="转录内容未找到，请先上传转录内容。",
            )

        #
        transcript_content = db.redis_upload_transcript.get_transcript(
            username=authenticated_user,
            time_stamp=request_data.time_stamp,
            file_number=request_data.file_number,
        )
        assert transcript_content != "", "转录内容不能为空"
        if transcript_content == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="转录内容不能为空。",
            )

        analyze_process_context = AnalyzeProcessContext(
            authenticated_user=authenticated_user,
            chat_history=[
                SystemMessage(
                    content=builtin_prompt.user_session_system_message(
                        authenticated_user,
                        db.redis_user.get_user_display_name(
                            username=authenticated_user
                        ),
                    )
                ),
                HumanMessage(content=builtin_prompt.event_segmentation_message()),
                HumanMessage(
                    content=builtin_prompt.transcript_message(
                        formatted_date=request_data.time_stamp.strftime("%Y-%m-%d"),
                        transcript_content=transcript_content,
                    )
                ),
            ],
            appservice_server=appservice_server,
        )

        # 步骤1~2: 标签提取过程
        execute_label_extraction(
            analyze_process_context=analyze_process_context,
        )
        # 如果标签提取过程未返回有效响应，则抛出异常
        if analyze_process_context._label_extraction_response is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="标签提取过程未返回有效响应。",
            )

        # 步骤3: 反思过程
        execute_reflection(
            analyze_process_context=analyze_process_context,
        )
        # 如果反思过程未返回有效响应，则抛出异常
        if analyze_process_context._reflection_response is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="反思过程未返回有效响应。",
            )

        # 计算执行时间并记录
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"分析过程总执行时间: {execution_time:.2f} 秒")

        # 返回分析结果
        return AnalyzeActionResponse(
            label_extraction=analyze_process_context._label_extraction_response,
            reflection=analyze_process_context._reflection_response,
            message=f"分析过程已完成 (用时: {execution_time:.2f}秒)",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################


@analyze_action_router.post(
    path="/action/upload_transcript/v1/", response_model=UploadTranscriptActionResponse
)
async def handle_upload_transcript_action(
    request_data: UploadTranscriptActionRequest,
    # appservice_server: AppserviceServerInstance,
    authenticated_user: str = Depends(get_authenticated_user),
) -> UploadTranscriptActionResponse:

    logger.info(f"/action/upload_transcript/v1/: {request_data.model_dump_json()}")

    try:

        assert request_data.transcript_content != "", "转录内容不能为空"
        if request_data.transcript_content == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="转录内容不能为空。",
            )

        if db.redis_upload_transcript.is_transcript_stored(
            username=authenticated_user,
            time_stamp=request_data.time_stamp,
            file_number=request_data.file_number,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该转录内容已存在，请勿重复上传。",
            )

        # 存储转录内容到 Redis
        db.redis_upload_transcript.store_transcript(
            username=authenticated_user,
            time_stamp=request_data.time_stamp,
            file_number=request_data.file_number,
            transcript_content=request_data.transcript_content,
            # expiration_time=60 * 60,  # 设置过期时间为1小时
        )
        logger.info(
            f"转录内容已存储: 用户={authenticated_user}, 时间戳={request_data.time_stamp}, 文件编号={request_data.file_number}"
        )

        return UploadTranscriptActionResponse(
            message=f"转录内容已存储: 用户={authenticated_user}, 时间戳={request_data.time_stamp}, 文件编号={request_data.file_number}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
