############################################################################################################
def main() -> None:

    import datetime

    # 启动 FastAPI 应用
    import uvicorn

    from app_services.app_service_server_app import app
    from loguru import logger
    from config.configuration import (
        AppserviceServerConfig,
        # USER_SESSION_SERVER_CONFIG_PATH,
        LOGS_DIR,
        LOCAL_HTTPS_ENABLED,
    )

    # assert (
    #     USER_SESSION_SERVER_CONFIG_PATH.exists()
    # ), f"找不到配置文件: {USER_SESSION_SERVER_CONFIG_PATH}"
    # config_file_content = USER_SESSION_SERVER_CONFIG_PATH.read_text(encoding="utf-8")
    # user_session_server_config = UserSessionServerConfig.model_validate_json(
    #     config_file_content
    # )

    app_service_config = AppserviceServerConfig()

    try:

        log_start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logger.add(LOGS_DIR / f"{log_start_time}.log", level="DEBUG")

        if LOCAL_HTTPS_ENABLED:
            # 本机回环测试https
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=app_service_config.server_port,
                ssl_keyfile="./localhost+3-key.pem",
                ssl_certfile="./localhost+3.pem",
            )
        else:
            # 正常测试的启动，可能有局域网的IP地址
            uvicorn.run(
                app,
                host=app_service_config.server_ip_address,
                port=app_service_config.server_port,
            )

    except Exception as e:
        logger.error(f"Exception: {e}")


############################################################################################################
if __name__ == "__main__":
    main()
