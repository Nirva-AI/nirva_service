from typing import Final, Dict, List, Union
from config.configuration import LLM_SERVER_CONFIG_PATH, LLMServerConfig
from llm_services.chat_service_request_manager import ChatServiceRequestManager
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import user_services.redis_client
from pydantic import BaseModel


###############################################################################################################################################
class UserSession(BaseModel):
    user_name: str
    chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = []


###############################################################################################################################################
class UserSessionManager:

    def __init__(self) -> None:
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
    def acquire_user_session(self, user_name: str) -> UserSession:
        redis_data = user_services.redis_client.redis_get(self._format_name(user_name))
        if redis_data == {} or redis_data is None:
            new_session = UserSession(
                user_name=user_name,
                chat_history=[
                    SystemMessage(
                        content="你需要扮演一个海盗与我对话，要用海盗的语气哦！"
                    )
                ],
            )

            self.update_user_session(new_session)
            return new_session

        return self._deserialize_user_session(redis_data)

    ###############################################################################################################################################
    def _format_name(self, user_name: str) -> str:
        return f"session:{user_name}"

    ###############################################################################################################################################
    def _serialize_user_session(self, user_session: UserSession) -> Dict[str, str]:
        return {
            "value": user_session.model_dump_json(),
        }

    ###############################################################################################################################################
    def _deserialize_user_session(self, session_data: Dict[str, str]) -> UserSession:
        return UserSession.model_validate_json(session_data["value"])

    ###############################################################################################################################################
    def update_user_session(self, user_session: UserSession) -> None:
        assert user_session.user_name != "", "用户会话必须有用户名"
        user_services.redis_client.redis_set(
            self._format_name(user_session.user_name),
            self._serialize_user_session(user_session),
        )

    ###############################################################################################################################################
    def delete_user_session(self, user_name: str) -> None:
        user_services.redis_client.redis_delete(self._format_name(user_name))

    ###############################################################################################################################################
