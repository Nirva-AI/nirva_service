from typing import Optional, Final
from user_services.user_session_manager import UserSessionManager
from llm_services.chat_service_request_manager import ChatServiceRequestManager
from config.configuration import LLM_SERVER_CONFIG_PATH, LLMServerConfig


###############################################################################################################################################
class UserSessionServer:

    _singleton: Optional["UserSessionServer"] = None

    def __init__(
        self,
        user_session_manager: UserSessionManager,
    ) -> None:

        self._user_session_manager: Final[UserSessionManager] = user_session_manager

        self._chat_service_request_manager: Final[ChatServiceRequestManager] = (
            self._initialize_chat_service_manager()
        )

    ###############################################################################################################################################
    @property
    def user_sessions(self) -> UserSessionManager:
        return self._user_session_manager

    ###############################################################################################################################################
    @property
    def chat_service(self) -> ChatServiceRequestManager:
        return self._chat_service_request_manager

    ###############################################################################################################################################
    def _initialize_chat_service_manager(self) -> ChatServiceRequestManager:
        config_file_content = LLM_SERVER_CONFIG_PATH.read_text(encoding="utf-8")
        assert (
            LLM_SERVER_CONFIG_PATH.exists()
        ), f"找不到配置文件: {LLM_SERVER_CONFIG_PATH}"
        llm_server_config = LLMServerConfig.model_validate_json(config_file_content)
        return ChatServiceRequestManager(
            localhost_urls=[
                f"http://localhost:{llm_server_config.port}{llm_server_config.api}"
            ],
        )

    ###############################################################################################################################################
