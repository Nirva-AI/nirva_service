############################################################################################################
def main() -> None:

    # 启动 FastAPI 应用
    from langgraph_services.analyzer_server_app import app, analyzer_server_config
    from loguru import logger
    import uvicorn

    try:
        uvicorn.run(app, host="localhost", port=analyzer_server_config.port)
    except Exception as e:
        logger.error(f"Exception: {e}")


############################################################################################################
if __name__ == "__main__":
    main()
