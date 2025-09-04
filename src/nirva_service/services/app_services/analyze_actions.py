import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from loguru import logger

import nirva_service.db.pgsql_journal_file
import nirva_service.db.redis_task as redis_task
import nirva_service.db.redis_upload_transcript
import nirva_service.db.redis_user
import nirva_service.prompts.builtin as builtin_prompt
import nirva_service.utils.format_string as format_string
from nirva_service.models import (
    AnalyzeActionRequest,
    BackgroundTaskResponse,
    JournalFile,
    LabelExtractionResponse,
    ReflectionResponse,
    UploadTranscriptActionRequest,
    UploadTranscriptActionResponse,
)
# EventAnalysis is imported via models/__init__.py
from nirva_service.models.api import (
    IncrementalAnalyzeRequest,
    IncrementalAnalyzeResponse,
    GetEventsRequest,
    GetEventsResponse,
)
from nirva_service.models.journal import gen_fake_journal_file
from nirva_service.services.langgraph_services.langgraph_models import (
    RequestTaskMessageListType,
)
from nirva_service.services.langgraph_services.langgraph_request_task import (
    LanggraphRequestTask,
)

from .app_service_server import AppserviceServerInstance
from .oauth_user import get_authenticated_user


class AnalyzeProcessor:
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

    async def execute_label_extraction(self) -> None:
        """执行标签提取过程"""
        try:
            # 构建 LanggraphRequestTask 请求
            step1_2_request = LanggraphRequestTask(
                username=self._authenticated_user,
                prompt=builtin_prompt.label_extraction_message(),
                chat_history=cast(RequestTaskMessageListType, self._chat_history),
                timeout=60 * 5,
            )

            # 处理请求
            await self._appservice_server.langgraph_service.analyze(
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
            self._label_extraction_response = (
                LabelExtractionResponse.model_validate_json(json_content)
            )

            # 新的消息。
            messages = [
                HumanMessage(content=builtin_prompt.label_extraction_message()),
                AIMessage(content=step1_2_request.last_response_message_content),
            ]

            # 将消息添加到会话中， 最后添加。
            self._chat_history.extend(messages)

            # 记录标签提取响应
            if self._label_extraction_response:
                logger.info(
                    "Label extraction response:",
                    self._label_extraction_response.model_dump_json(),
                )

        except Exception as e:
            logger.error("Failed to execute label extraction:", e)
            raise e

    async def execute_reflection(self) -> None:
        """执行反思过程"""
        try:
            # 构建 LanggraphRequestTask 请求
            step3_request = LanggraphRequestTask(
                username=self._authenticated_user,
                prompt=builtin_prompt.reflection_message(),
                chat_history=cast(RequestTaskMessageListType, self._chat_history),
                timeout=60 * 5,
            )

            # 处理请求
            await self._appservice_server.langgraph_service.analyze(
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
            self._reflection_response = ReflectionResponse.model_validate_json(
                json_content
            )

            # 新的消息。
            messages = [
                HumanMessage(content=builtin_prompt.reflection_message()),
                AIMessage(content=step3_request.last_response_message_content),
            ]

            # 将消息添加到会话中
            self._chat_history.extend(messages)

            # 记录反思响应
            if self._reflection_response:
                logger.info(
                    "Reflection response:",
                    self._reflection_response.model_dump_json(),
                )

        except Exception as e:
            logger.error("Failed to execute reflection:", e)
            raise e


###################################################################################################################################################################
async def _analyze_task(
    username: str,
    task_id: str,
    request_data: AnalyzeActionRequest,
    appservice_server: AppserviceServerInstance,
) -> None:
    """后台处理分析任务"""
    try:
        # 更新任务状态为处理中
        redis_task.update_task_status(
            username=username, task_id=task_id, status=redis_task.TaskStatus.PROCESSING
        )

        # 开始计时
        start_time = time.time()

        # 检查是否已存在日记文件
        journal_file_db = nirva_service.db.pgsql_journal_file.get_journal_file(
            username=username,
            time_stamp=request_data.time_stamp,
        )

        if journal_file_db is not None:
            # 如果已经存在日记文件，直接返回
            logger.info(
                f"已存在日记文件: 用户={username}, 时间戳={request_data.time_stamp}"
            )
            journal_file = JournalFile.model_validate_json(journal_file_db.content_json)

            # 更新任务状态为完成并存储结果
            redis_task.update_task_status(
                username=username,
                task_id=task_id,
                status=redis_task.TaskStatus.COMPLETED,
                result={"journal_file": journal_file.model_dump()},
            )
            return

        # 检查转录内容
        if not nirva_service.db.redis_upload_transcript.is_transcript_stored(
            username=username,
            time_stamp=request_data.time_stamp,
        ):
            redis_task.update_task_status(
                username=username,
                task_id=task_id,
                status=redis_task.TaskStatus.FAILED,
                error="转录内容未找到，请先上传转录内容。",
            )
            return

        # 获取转录内容
        transcript_content = nirva_service.db.redis_upload_transcript.get_transcript(
            username=username,
            time_stamp=request_data.time_stamp,
        )
        if transcript_content.strip() == "":
            redis_task.update_task_status(
                username=username,
                task_id=task_id,
                status=redis_task.TaskStatus.FAILED,
                error="转录内容不能为空。",
            )
            return

        # TODO: 使用测试数据模式，模拟真实流程延迟
        USE_FAKE_DATA = True  # 设置为False时使用真实处理流程

        if USE_FAKE_DATA:
            logger.info("使用测试数据模式，模拟处理流程延迟")

            # 模拟步骤1~2: 标签提取过程的延迟 (通常2-3秒)
            logger.info("开始执行标签提取过程...")
            await asyncio.sleep(2.5)
            logger.info("标签提取过程完成")

            # 模拟步骤3: 反思过程的延迟 (通常3-4秒)
            logger.info("开始执行反思过程...")
            await asyncio.sleep(3.5)
            logger.info("反思过程完成")

            # 生成测试数据
            journal_file = gen_fake_journal_file(
                authenticated_user=username,
                time_stamp=request_data.time_stamp,
            )

        else:
            # 正式的分析步骤
            analyze_process_context = AnalyzeProcessor(
                authenticated_user=username,
                chat_history=[
                    SystemMessage(
                        content=builtin_prompt.user_session_system_message(
                            username,
                            nirva_service.db.redis_user.get_user_display_name(
                                username=username
                            ),
                        )
                    ),
                    HumanMessage(content=builtin_prompt.event_segmentation_message()),
                    HumanMessage(
                        content=builtin_prompt.transcript_message(
                            formatted_date=request_data.time_stamp,
                            transcript_content=transcript_content,
                        )
                    ),
                ],
                appservice_server=appservice_server,
            )

            # 步骤1~2: 标签提取过程
            await analyze_process_context.execute_label_extraction()
            if analyze_process_context._label_extraction_response is None:
                redis_task.update_task_status(
                    username=username,
                    task_id=task_id,
                    status=redis_task.TaskStatus.FAILED,
                    error="标签提取过程未返回有效响应。",
                )
                return

            # 步骤3: 反思过程
            await analyze_process_context.execute_reflection()
            if analyze_process_context._reflection_response is None:
                redis_task.update_task_status(
                    username=username,
                    task_id=task_id,
                    status=redis_task.TaskStatus.FAILED,
                    error="反思过程未返回有效响应。",
                )
                return

            # 构建数据
            journal_file = JournalFile(
                username=username,
                time_stamp=request_data.time_stamp,
                events=analyze_process_context._label_extraction_response.events,
                daily_reflection=analyze_process_context._reflection_response.daily_reflection,
            )

            for event in journal_file.events:
                # 放弃LLM生成的id，自己全部重新赋值。
                event.event_id = str(uuid.uuid4())

        # 存储到数据库
        nirva_service.db.pgsql_journal_file.save_or_update_journal_file(
            username=username,
            journal_file=journal_file,
        )

        # 计算执行时间
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"分析过程总执行时间: {execution_time:.2f} 秒")

        # 更新任务状态为完成
        redis_task.update_task_status(
            username=username,
            task_id=task_id,
            status=redis_task.TaskStatus.COMPLETED,
            result={"journal_file": journal_file.model_dump()},
        )

    except Exception as e:
        logger.error(f"处理分析任务失败: {e}")
        redis_task.update_task_status(
            username=username,
            task_id=task_id,
            status=redis_task.TaskStatus.FAILED,
            error=str(e),
        )


###################################################################################################################################################################
analyze_action_router = APIRouter()


###################################################################################################################################################################
# 增量分析API
###################################################################################################################################################################

@analyze_action_router.post(
    path="/action/analyze/incremental/v1/", response_model=IncrementalAnalyzeResponse
)
async def handle_incremental_analyze(
    request_data: IncrementalAnalyzeRequest,
    appservice_server: AppserviceServerInstance,
    authenticated_user: str = Depends(get_authenticated_user),
) -> IncrementalAnalyzeResponse:
    """处理增量转录分析"""

    logger.info(f"/action/analyze/incremental/v1/: {request_data.model_dump_json()}")

    try:
        # 导入增量分析器
        from .incremental_analyzer import IncrementalAnalyzer
        
        # 创建增量分析器
        analyzer = IncrementalAnalyzer(appservice_server.langgraph_service)
        
        # 处理增量转录
        result = await analyzer.process_incremental_transcript(
            username=authenticated_user,
            time_stamp=request_data.time_stamp,
            new_transcript=request_data.new_transcript
        )
        
        logger.info(f"增量分析完成: {result.message}")
        return result

    except Exception as e:
        logger.error(f"增量分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"增量分析失败: {e}",
        )


###################################################################################################################################################################
@analyze_action_router.post(
    path="/action/analyze/events/get/v1/", response_model=GetEventsResponse
)
async def handle_get_events(
    request_data: GetEventsRequest,
    authenticated_user: str = Depends(get_authenticated_user),
) -> GetEventsResponse:
    """获取指定日期的所有事件"""

    logger.info(f"/action/analyze/events/get/v1/: {request_data.model_dump_json()}")

    try:
        # 从数据库获取JournalFile
        journal_db = nirva_service.db.pgsql_journal_file.get_journal_file(
            username=authenticated_user,
            time_stamp=request_data.time_stamp
        )
        
        if not journal_db:
            # 如果没有找到，返回空的事件列表
            return GetEventsResponse(
                time_stamp=request_data.time_stamp,
                events=[],
                total_count=0,
                last_updated="未找到数据"
            )
        
        # 解析JournalFile内容
        import json
        journal_data = json.loads(journal_db.content_json)
        journal_file = JournalFile.model_validate(journal_data)
        
        # 返回事件列表
        return GetEventsResponse(
            time_stamp=request_data.time_stamp,
            events=journal_file.events,
            total_count=len(journal_file.events),
            last_updated=journal_db.updated_at.isoformat() if journal_db.updated_at else "未知"
        )

    except Exception as e:
        logger.error(f"获取事件列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取事件列表失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@analyze_action_router.post(
    path="/action/analyze/v1/", response_model=BackgroundTaskResponse
)
async def handle_analyze(
    request_data: AnalyzeActionRequest,
    background_tasks: BackgroundTasks,
    appservice_server: AppserviceServerInstance,
    authenticated_user: str = Depends(get_authenticated_user),
) -> BackgroundTaskResponse:
    """创建分析任务并在后台执行"""

    logger.info(f"/action/analyze/v1/: {request_data.model_dump_json()}")

    try:
        # 创建任务并获取任务ID
        task_id = redis_task.create_task(
            username=authenticated_user, task_type="analyze_action"
        )

        # 将实际处理作为后台任务
        background_tasks.add_task(
            _analyze_task,
            username=authenticated_user,
            task_id=task_id,
            request_data=request_data,
            appservice_server=appservice_server,
        )

        return BackgroundTaskResponse(
            task_id=task_id,
            message="分析任务已创建，请使用任务ID查询状态和结果",
        )

    except Exception as e:
        logger.error(f"创建分析任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建分析任务失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################


@analyze_action_router.get(
    path="/action/task/status/v1/{task_id}/", response_model=Dict[str, Any]
)
async def get_task_status(
    task_id: str,
    authenticated_user: str = Depends(get_authenticated_user),
) -> Dict[str, Any]:
    """查询任务状态和结果"""

    task_data = redis_task.get_task_status(username=authenticated_user, task_id=task_id)

    if not task_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在或已过期"
        )

    return task_data


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@analyze_action_router.get(
    path="/action/get_journal_file/v1/{time_stamp}/", response_model=JournalFile
)
async def get_journal_file(
    time_stamp: str,
    authenticated_user: str = Depends(get_authenticated_user),
) -> JournalFile:
    """获取用户的日记文件"""

    logger.info(f"/action/get_journal_file/v1/{time_stamp}/")

    try:
        # 从数据库获取日记文件
        journal_file_db = nirva_service.db.pgsql_journal_file.get_journal_file(
            username=authenticated_user, time_stamp=time_stamp
        )

        if journal_file_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"日记文件未找到: 用户={authenticated_user}, 时间戳={time_stamp}",
            )

        # 返回实际的日记文件
        return JournalFile.model_validate_json(journal_file_db.content_json)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取日记文件失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################


@analyze_action_router.get(
    path="/action/get_events_by_date/v1/", response_model=JournalFile
)
async def get_events_by_date(
    date: str,  # Format: YYYY-MM-DD
    timezone: str = "UTC",  # e.g., "America/Los_Angeles", "UTC", etc.
    authenticated_user: str = Depends(get_authenticated_user),
) -> JournalFile:
    """
    Get events for a specific date in the user's timezone.
    
    Args:
        date: Date in YYYY-MM-DD format (in the user's timezone)
        timezone: User's timezone (e.g., "America/Los_Angeles")
        authenticated_user: Username from authentication
    
    Returns:
        JournalFile with events that occurred on the specified date in the user's timezone
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    
    logger.info(f"/action/get_events_by_date/v1/: date={date}, timezone={timezone}, user={authenticated_user}")
    
    try:
        # Parse the date and create start/end times in the user's timezone
        user_tz = ZoneInfo(timezone)
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        
        # Create start and end of day in user's timezone
        start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=user_tz)
        end_of_day = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=user_tz)
        
        # Convert to UTC for comparison
        start_utc = start_of_day.astimezone(ZoneInfo('UTC'))
        end_utc = end_of_day.astimezone(ZoneInfo('UTC'))
        
        # Get all events for the user
        all_events_journal = nirva_service.db.pgsql_journal_file.get_journal_file(
            username=authenticated_user, time_stamp='all_events'
        )
        
        if all_events_journal is None:
            # Return empty journal for the date
            return JournalFile(
                username=authenticated_user,
                time_stamp=date,
                events=[],
                daily_reflection=None
            )
        
        # Parse the journal
        journal = JournalFile.model_validate_json(all_events_journal.content_json)
        
        # Filter events by date range
        filtered_events = []
        for event in journal.events:
            if event.start_timestamp:
                # Ensure timestamp is timezone-aware
                if event.start_timestamp.tzinfo is None:
                    event_time = event.start_timestamp.replace(tzinfo=ZoneInfo('UTC'))
                else:
                    event_time = event.start_timestamp
                
                # Check if event falls within the requested date in user's timezone
                if start_utc <= event_time <= end_utc:
                    filtered_events.append(event)
        
        # Return journal with filtered events
        return JournalFile(
            username=authenticated_user,
            time_stamp=date,
            events=filtered_events,
            daily_reflection=journal.daily_reflection
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format or timezone: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get events: {e}"
        )


@analyze_action_router.post(
    path="/action/upload_transcript/v1/", response_model=UploadTranscriptActionResponse
)
async def handle_upload_transcript(
    request_data: UploadTranscriptActionRequest,
    authenticated_user: str = Depends(get_authenticated_user),
) -> UploadTranscriptActionResponse:
    logger.info(f"/action/upload_transcript/v1/: {request_data.model_dump_json()}")

    try:
        # 验证转录列表不能为空
        if not request_data.transcripts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="转录列表不能为空。",
            )

        # 批量存储转录内容到 Redis
        results = nirva_service.db.redis_upload_transcript.store_transcripts_batch(
            username=authenticated_user,
            transcripts=request_data.transcripts,
            # expiration_time=60 * 60,  # 设置过期时间为1小时
        )

        # 记录日志
        logger.info(
            f"批量转录内容处理完成: 用户={authenticated_user}, 处理数量={len(results)}"
        )

        # 返回成功响应
        return UploadTranscriptActionResponse(
            results=results,
            message=f"批量转录内容处理完成: 用户={authenticated_user}, 处理数量={len(results)}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
