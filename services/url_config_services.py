from fastapi import APIRouter, Request
from loguru import logger
from models_v_0_0_1 import (
    URLConfigurationResponse,
)

###################################################################################################################################################################
url_config_router = APIRouter()


###################################################################################################################################################################
@url_config_router.get(path="/config", response_model=URLConfigurationResponse)
async def api_endpoints(
    request: Request,
) -> URLConfigurationResponse:

    base = str(request.base_url)
    logger.info(f"URLConfigurationResponse: {base}")

    # 获取请求的基础URL（含http(s)://域名）
    return URLConfigurationResponse(
        api_version="v1",
        endpoints={
            "login": base + "login/v1/",
            "logout": base + "logout/v1/",
            "chat": base + "action/chat/v1/",
        },
    )


###################################################################################################################################################################
