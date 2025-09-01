from typing import Dict
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from loguru import logger

from ...config.configuration import AnalyzerServerConfig
from .chat_llm_graph import (
    State,
    create_compiled_stage_graph,
    stream_graph_updates,
)
from .langgraph_models import LanggraphRequest, LanggraphResponse
from .langgraph_service import LanggraphService
from .transcription_processor import TranscriptionProcessor

analyzer_server_config = AnalyzerServerConfig()

# Initialize services
# Note: LanggraphService will be initialized properly in production
# For now, create a placeholder that will be set up when needed
transcription_processor = None

############################################################################################################
# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global transcription_processor
    
    # Startup
    logger.info("Starting analyzer server...")
    
    # Initialize LanggraphService with proper configuration
    from ...config.configuration import ChatServerConfig
    chat_config = ChatServerConfig()
    
    langgraph_service = LanggraphService(
        chat_service_localhost_urls=[f"http://localhost:{chat_config.port}/chat/v1/"],
        chat_service_test_get_urls=[f"http://localhost:{chat_config.port}/test_get"],
        analyzer_service_localhost_urls=[f"http://localhost:{analyzer_server_config.port}/analyze/v1/"],
        analyzer_service_test_get_urls=[f"http://localhost:{analyzer_server_config.port}/test_get"]
    )
    
    # Create transcription processor
    transcription_processor = TranscriptionProcessor(
        langgraph_service=langgraph_service,
        process_interval_seconds=120  # 2 minutes
    )
    
    await transcription_processor.start()
    logger.info("Transcription processor started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down analyzer server...")
    if transcription_processor:
        await transcription_processor.stop()
    logger.info("Transcription processor stopped")

############################################################################################################
# 初始化 FastAPI 应用
app = FastAPI(
    title=analyzer_server_config.fast_api_title,
    version=analyzer_server_config.fast_api_version,
    description=analyzer_server_config.fast_api_description,
    lifespan=lifespan
)
############################################################################################################
# 创建状态图
compiled_state_graph = create_compiled_stage_graph(
    "analyzer_llm_node", analyzer_server_config.temperature
)


############################################################################################################
############################################################################################################
############################################################################################################
@app.post(
    path=str(analyzer_server_config.analyze_service_api),
    response_model=LanggraphResponse,
)
async def handle_analyze_request(
    request_data: LanggraphRequest,
) -> LanggraphResponse:
    try:
        # 聊天历史
        chat_history_state: State = {
            "messages": [message for message in request_data.chat_history]
        }

        # 用户输入
        user_input_state: State = {"messages": [request_data.message]}

        # 获取回复
        update_messages = stream_graph_updates(
            state_compiled_graph=compiled_state_graph,
            chat_history_state=chat_history_state,
            user_input_state=user_input_state,
        )

        # 返回响应
        if len(update_messages) > 0:
            return LanggraphResponse(
                messages=update_messages,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="没有生成任何回复，请稍后再试。",
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )


############################################################################################################
############################################################################################################
############################################################################################################
# 定义测试GET请求的路由
@app.get(path=str(analyzer_server_config.test_get_api))
async def handle_test_get_request() -> Dict[str, str]:
    """
    简单的GET端点，用于测试服务是否正常运行
    """
    return {
        "status": "ok",
        "message": "Chat服务运行正常",
        "version": analyzer_server_config.fast_api_version,
        "service": analyzer_server_config.fast_api_title,
    }


############################################################################################################
# Transcription Processor Monitoring Endpoints
############################################################################################################

@app.get("/transcription-processor/status")
async def get_processor_status() -> Dict:
    """
    Get the current status of the transcription processor.
    
    Returns:
        Status information including counts and statistics
    """
    if not transcription_processor:
        return {
            "is_running": False,
            "message": "Transcription processor not initialized yet"
        }
    
    try:
        return transcription_processor.get_status()
    except Exception as e:
        logger.error(f"Error getting processor status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processor status: {e}"
        )


@app.get("/transcription-processor/stats")
async def get_processor_statistics() -> Dict:
    """
    Get detailed statistics from the transcription processor.
    
    Returns:
        Detailed statistics including processing metrics
    """
    if not transcription_processor:
        return {
            "message": "Transcription processor not initialized yet"
        }
    
    try:
        return transcription_processor.get_statistics()
    except Exception as e:
        logger.error(f"Error getting processor statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processor statistics: {e}"
        )


@app.post("/transcription-processor/trigger")
async def trigger_processing() -> Dict:
    """
    Manually trigger transcription processing.
    Useful for testing or forcing immediate processing.
    
    Returns:
        Processing results
    """
    if not transcription_processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transcription processor not initialized yet"
        )
    
    try:
        logger.info("Manual transcription processing triggered via API")
        result = await transcription_processor.trigger_manual_processing()
        return {
            "status": "success",
            "message": "Processing triggered successfully",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error triggering manual processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger processing: {e}"
        )


############################################################################################################
############################################################################################################
############################################################################################################
