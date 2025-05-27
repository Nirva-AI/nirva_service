from typing import Final, Optional, Dict
from config.configuration import LLM_SERVER_CONFIG_PATH, LLMServerConfig
from llm_services.chat_service_request_manager import ChatServiceRequestManager
from user_services.user_session import UserSession


class UserSessionManager:

    def __init__(self) -> None:
        self._user_sessions: Dict[str, UserSession] = {}
        self._chat_service_request_manager: Final[ChatServiceRequestManager] = (
            self._create_chat_service_request_manager()
        )

    ###############################################################################################################################################
    @property
    def chat_service_request_manager(self) -> ChatServiceRequestManager:
        return self._chat_service_request_manager

    ###############################################################################################################################################
    def _create_chat_service_request_manager(self) -> ChatServiceRequestManager:
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
    def acquire_user_session(self, user_name: str) -> Optional[UserSession]:
        if not user_name in self._user_sessions:
            self._user_sessions[user_name] = UserSession(user_name)

        return self._user_sessions.get(user_name, None)

    ###############################################################################################################################################
    def delete_user_session(self, user_name: str) -> None:
        if user_name in self._user_sessions:
            self._user_sessions.pop(user_name, None)

    ###############################################################################################################################################
