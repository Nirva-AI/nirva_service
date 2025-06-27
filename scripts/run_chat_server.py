import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


############################################################################################################
def main() -> None:
    # 启动 FastAPI 应用
    import uvicorn
    from loguru import logger

    from nirva_service.services.langgraph_services.chat_server_fastapi import (
        app,
        chat_server_config,
    )

    try:
        uvicorn.run(app, host="localhost", port=chat_server_config.port)
    except Exception as e:
        logger.error(f"Exception: {e}")


############################################################################################################
if __name__ == "__main__":
    main()
