import datetime
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from services.user_session_server_instance import (
    UserSessionServerInstance,
    initialize_user_session_server_instance,
)
from config.configuration import (
    UserSessionServerConfig,
    USER_SESSION_SERVER_CONFIG_PATH,
    LOGS_DIR,
)


###############################################################################################################################################
def _setup_logger() -> None:
    log_start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logger.add(LOGS_DIR / f"{log_start_time}.log", level="DEBUG")


###############################################################################################################################################
def _launch_user_session_server(game_server: UserSessionServerInstance) -> None:
    import uvicorn

    from services.api_endpoints_services import api_endpoints_router
    from services.login_services import login_router
    from services.chat_action_services import chat_action_router

    #
    game_server.fast_api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    game_server.fast_api.include_router(router=api_endpoints_router)
    game_server.fast_api.include_router(router=login_router)
    game_server.fast_api.include_router(router=chat_action_router)

    uvicorn.run(
        game_server.fast_api,
        host=game_server._server_config.server_ip_address,
        port=game_server._server_config.server_port,
    )


###############################################################################################################################################
def main() -> None:

    try:
        assert (
            USER_SESSION_SERVER_CONFIG_PATH.exists()
        ), f"找不到配置文件: {USER_SESSION_SERVER_CONFIG_PATH}"
        config_file_content = USER_SESSION_SERVER_CONFIG_PATH.read_text(
            encoding="utf-8"
        )
        user_session_server_config = UserSessionServerConfig.model_validate_json(
            config_file_content
        )

        _setup_logger()

        _launch_user_session_server(
            initialize_user_session_server_instance(
                server_ip_address=user_session_server_config.local_network_ip,
                server_port=user_session_server_config.server_port,
                local_network_ip=user_session_server_config.local_network_ip,
            )
        )

    except Exception as e:
        print(f"Exception: {e}")


###############################################################################################################################################
if __name__ == "__main__":
    main()
