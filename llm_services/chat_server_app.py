import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from fastapi import FastAPI, HTTPException, status
from llm_services.langgraph_models import (
    LanggraphRequest,
    LanggraphResponse,
)
from llm_services.chat_azure_openai_gpt_4o_graph import (
    create_compiled_stage_graph,
    stream_graph_updates,
    State,
)
from config.configuration import ChatServerConfig

llm_server_config = ChatServerConfig()
############################################################################################################
# 初始化 FastAPI 应用
app = FastAPI(
    title=llm_server_config.fast_api_title,
    version=llm_server_config.fast_api_version,
    description=llm_server_config.fast_api_description,
)
############################################################################################################
# 创建状态图
compiled_state_graph = create_compiled_stage_graph(
    "azure_chat_openai_chatbot_node", llm_server_config.temperature
)


############################################################################################################
############################################################################################################
############################################################################################################
# 定义处理聊天请求的路由
@app.post(path=str(llm_server_config.api), response_model=LanggraphResponse)
async def process_chat_request(
    request_data: LanggraphRequest,
) -> LanggraphResponse:

    try:
        # 聊天历史
        chat_history_state: State = {
            "messages": [message for message in request_data.chat_history]
        }

        # 用户输入
        user_input_state: State = {"messages": [request_data.message]}

        # 获取回复
        update_messages = stream_graph_updates(
            state_compiled_graph=compiled_state_graph,
            chat_history_state=chat_history_state,
            user_input_state=user_input_state,
        )

        # 返回响应
        if len(update_messages) > 0:
            return LanggraphResponse(
                messages=update_messages,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="没有生成任何回复，请稍后再试。",
            )

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {e}",
        )
