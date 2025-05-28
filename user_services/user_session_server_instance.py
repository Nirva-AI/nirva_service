from user_services.user_session_server import UserSessionServer
from fastapi import Depends
from typing import Annotated, Optional
from llm_services.chat_service_request_manager import ChatServiceRequestManager
from config.configuration import LLM_SERVER_CONFIG_PATH, LLMServerConfig
from user_services.user_session_manager import UserSessionManager


###############################################################################################################################################

_user_session_instance: Optional["UserSessionServer"] = None


###############################################################################################################################################


def _initialize_chat_service_manager() -> ChatServiceRequestManager:
    config_file_content = LLM_SERVER_CONFIG_PATH.read_text(encoding="utf-8")
    assert LLM_SERVER_CONFIG_PATH.exists(), f"找不到配置文件: {LLM_SERVER_CONFIG_PATH}"
    llm_server_config = LLMServerConfig.model_validate_json(config_file_content)
    return ChatServiceRequestManager(
        localhost_urls=[
            f"http://localhost:{llm_server_config.port}{llm_server_config.api}"
        ],
    )


###############################################################################################################################################
def get_user_session_server_instance() -> UserSessionServer:

    global _user_session_instance
    if _user_session_instance is None:
        _user_session_instance = UserSessionServer(
            user_session_manager=UserSessionManager(),
            chat_service_request_manager=_initialize_chat_service_manager(),
        )

    assert (
        _user_session_instance is not None
    ), "UserSessionServer instance is not initialized."
    return _user_session_instance


###############################################################################################################################################
UserSessionServerInstance = Annotated[
    UserSessionServer, Depends(get_user_session_server_instance)
]
###############################################################################################################################################
