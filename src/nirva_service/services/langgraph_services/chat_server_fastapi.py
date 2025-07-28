from typing import Dict

from fastapi import FastAPI, HTTPException, status

from ...config.configuration import ChatServerConfig
from .chat_azure_openai_gpt_4o_graph import (
    State,
    create_compiled_stage_graph,
    stream_graph_updates,
)
from .langgraph_models import LanggraphRequest, LanggraphResponse

chat_server_config = ChatServerConfig()
############################################################################################################
# 初始化 FastAPI 应用
app = FastAPI(
    title=chat_server_config.fast_api_title,
    version=chat_server_config.fast_api_version,
    description=chat_server_config.fast_api_description,
)
############################################################################################################
# 创建状态图
compiled_state_graph = create_compiled_stage_graph(
    "openai_chat_chatbot_node", chat_server_config.temperature
)


############################################################################################################
############################################################################################################
############################################################################################################
# 定义处理聊天请求的路由
@app.post(
    path=str(chat_server_config.chat_service_api), response_model=LanggraphResponse
)
async def handle_chat_request(
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


############################################################################################################
############################################################################################################
############################################################################################################
# 定义测试GET请求的路由
@app.get(path=str(chat_server_config.test_get_api))
async def handle_test_get_request() -> Dict[str, str]:
    """
    简单的GET端点，用于测试服务是否正常运行
    """
    return {
        "status": "ok",
        "message": "Chat服务运行正常",
        "version": chat_server_config.fast_api_version,
        "service": chat_server_config.fast_api_title,
    }


############################################################################################################
############################################################################################################
############################################################################################################
