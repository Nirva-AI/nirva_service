############################################################################################################
def main() -> None:

    # 启动 FastAPI 应用
    from llm_services.chat_server_app import app, llm_server_config
    from loguru import logger
    import uvicorn

    try:
        uvicorn.run(app, host="localhost", port=llm_server_config.port)
    except Exception as e:
        logger.error(f"Exception: {e}")


############################################################################################################
if __name__ == "__main__":
    main()
