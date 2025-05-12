import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from typing import Final, cast, final
from fastapi import FastAPI
from langchain.schema import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from llm_serves.chat_service_api import (
    ChatServiceRequest,
    ChatServiceResponse,
)
from llm_serves.azure_chat_openai_gpt_4o_graph import (
    create_compiled_stage_graph,
    stream_graph_updates,
    State,
)
from config.configuration import LLMServerConfig, LLM_SERVER_CONFIG_PATH
from loguru import logger


############################################################################################################
@final
class ChatProcessor:

    def __init__(self, api: str, compiled_state_graph: CompiledStateGraph) -> None:
        self._api: Final[str] = api
        self._compiled_state_graph: Final[CompiledStateGraph] = compiled_state_graph

    ############################################################################################################
    @property
    def post_url(self) -> str:
        return self._api

    ############################################################################################################
    def process_chat_request(self, request: ChatServiceRequest) -> ChatServiceResponse:

        # 聊天历史
        chat_history_state: State = {
            "messages": [message for message in request.chat_history]
        }

        # 用户输入
        user_input_state: State = {"messages": [HumanMessage(content=request.input)]}

        # 获取回复
        update_messages = stream_graph_updates(
            state_compiled_graph=self._compiled_state_graph,
            chat_history_state=chat_history_state,
            user_input_state=user_input_state,
        )

        # 返回
        if len(update_messages) > 0:
            return ChatServiceResponse(
                # agent_name=request.agent_name,
                user_name=request.user_name,
                output=cast(str, update_messages[-1].content),
            )
        return ChatServiceResponse(user_name=request.user_name, output="")


############################################################################################################
def launch_localhost_chat_server(
    app: FastAPI, port: int, chat_executor: ChatProcessor
) -> None:

    @app.post(path=chat_executor.post_url, response_model=ChatServiceResponse)
    async def process_chat_request(
        request_data: ChatServiceRequest,
    ) -> ChatServiceResponse:
        return chat_executor.process_chat_request(request_data)

    # 启动 FastAPI 应用
    import uvicorn

    uvicorn.run(app, host="localhost", port=port)


############################################################################################################
def main() -> None:

    try:

        assert (
            LLM_SERVER_CONFIG_PATH.exists()
        ), f"找不到配置文件: {LLM_SERVER_CONFIG_PATH}"
        config_file_content = LLM_SERVER_CONFIG_PATH.read_text(encoding="utf-8")
        llm_server_config = LLMServerConfig.model_validate_json(config_file_content)

        app = FastAPI(
            title=llm_server_config.fast_api_title,
            version=llm_server_config.fast_api_version,
            description=llm_server_config.fast_api_description,
        )

        chat_executor = ChatProcessor(
            api=str(llm_server_config.api),
            compiled_state_graph=create_compiled_stage_graph(
                "azure_chat_openai_chatbot_node", llm_server_config.temperature
            ),
        )

        launch_localhost_chat_server(
            app=app,
            port=llm_server_config.port,
            chat_executor=chat_executor,
        )

    except Exception as e:
        logger.error(f"Exception: {e}")


############################################################################################################
if __name__ == "__main__":
    main()
