from llm_service.chat_server import app, llm_server_config
from loguru import logger


############################################################################################################
def main() -> None:
    try:
        # 启动 FastAPI 应用
        import uvicorn

        uvicorn.run(app, host="localhost", port=llm_server_config.port)

    except Exception as e:
        logger.error(f"Exception: {e}")


############################################################################################################
if __name__ == "__main__":
    main()
