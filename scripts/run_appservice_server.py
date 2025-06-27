import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


############################################################################################################
def main() -> None:
    import datetime

    # 启动 FastAPI 应用
    import uvicorn
    from loguru import logger

    from nirva_service.config.configuration import (
        LOCAL_HTTPS_ENABLED,
        LOGS_DIR,
        AppserviceServerConfig,
    )
    from nirva_service.services.app_services.appservice_server_fastapi import app

    appservice_config = AppserviceServerConfig()

    try:
        log_start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logger.add(LOGS_DIR / f"{log_start_time}.log", level="DEBUG")

        if LOCAL_HTTPS_ENABLED:
            # 本机回环测试https
            project_root = Path(__file__).parent.parent
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=appservice_config.server_port,
                ssl_keyfile=str(project_root / "localhost+3-key.pem"),
                ssl_certfile=str(project_root / "localhost+3.pem"),
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
