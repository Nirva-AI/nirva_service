from fastapi import APIRouter, Request
from loguru import logger

from nirva_service.models import URLConfigurationResponse

# **API网关或反向代理：通过在服务器端设置API网关，让客户端始终请求固定的域名和路径，由网关转发到实际服务。
# 这样即使后端架构调整（比如拆分服务到不同子域或路径），客户端也无需改动。
# 这种方式将动态调整放在服务器基础设施层面，而非交由客户端处理，更符合"客户端简单、服务器智能"**的理念。

###################################################################################################################################################################
url_config_router = APIRouter()


###################################################################################################################################################################
@url_config_router.get(path="/config", response_model=URLConfigurationResponse)
async def get_url_config(
    request: Request,
) -> URLConfigurationResponse:
    base = str(request.base_url)
    logger.info(f"URLConfigurationResponse: {base}")

    # 获取请求的基础URL（含http(s)://域名）
    return URLConfigurationResponse(
        api_version="v1",
        endpoints={
            "login": base + "login/v1/",
            "refresh": base + "refresh/v1/",
            "logout": base + "logout/v1/",
            "chat": base + "action/chat/v1/",
            "analyze": base + "action/analyze/v1/",
            "upload_transcript": base + "action/upload_transcript/v1/",
            "task_status": base + "action/task/status/v1/{task_id}/",
            "get_journal_file": base + "action/get_journal_file/v1/{time_stamp}/",
            "get_events": base + "action/analyze/events/get/v1/",
            "incremental_analyze": base + "action/analyze/incremental/v1/",
        },
    )


###################################################################################################################################################################
