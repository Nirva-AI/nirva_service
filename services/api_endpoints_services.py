from fastapi import APIRouter
from loguru import logger
from services.user_session_server_instance import UserSessionServerInstance
from models_v_0_0_1 import (
    APIEndpointConfiguration,
    APIEndpointConfigurationResponse,
)

###################################################################################################################################################################
api_endpoints_router = APIRouter()


###################################################################################################################################################################
@api_endpoints_router.post(
    path="/api_endpoints/v1/", response_model=APIEndpointConfigurationResponse
)
async def api_endpoints(
    game_server: UserSessionServerInstance,
) -> APIEndpointConfigurationResponse:

    logger.info("获取API路由")

    server_ip_address = str(game_server.server_ip_address)
    if server_ip_address == "0.0.0.0":
        # TODO, 这里需要改成获取本机的ip地址
        server_ip_address = game_server.local_network_ip
        logger.info(f"0.0.0.0, use local ip address: {server_ip_address}")

    server_port = game_server.server_port

    generated_api_endpoints: APIEndpointConfiguration = APIEndpointConfiguration(
        LOGIN_URL=f"http://{server_ip_address}:{server_port}/login/v1/",
        LOGOUT_URL=f"http://{server_ip_address}:{server_port}/logout/v1/",
        CHAT_ACTION_URL=f"http://{server_ip_address}:{server_port}/chat-action/v1/",
    )

    return APIEndpointConfigurationResponse(
        message="获取API路由成功",
        api_endpoints=generated_api_endpoints,
    )


###################################################################################################################################################################
