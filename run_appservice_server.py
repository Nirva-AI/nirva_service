############################################################################################################
def main() -> None:

    import datetime

    # 启动 FastAPI 应用
    import uvicorn

    from app_services.appservice_server_fastapi import app
    from loguru import logger
    from config.configuration import (
        AppserviceServerConfig,
        LOGS_DIR,
        LOCAL_HTTPS_ENABLED,
    )

    appservice_config = AppserviceServerConfig()

    try:

        log_start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logger.add(LOGS_DIR / f"{log_start_time}.log", level="DEBUG")

        if LOCAL_HTTPS_ENABLED:
            # 本机回环测试https
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=appservice_config.server_port,
                ssl_keyfile="./localhost+3-key.pem",
                ssl_certfile="./localhost+3.pem",
            )
        else:
            # 正常测试的启动，可能有局域网的IP地址
            uvicorn.run(
                app,
                host=appservice_config.server_ip_address,
                port=appservice_config.server_port,
            )

    except Exception as e:
        logger.error(f"Exception: {e}")


############################################################################################################
if __name__ == "__main__":
    main()
