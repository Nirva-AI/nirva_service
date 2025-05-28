from typing import Final
from user_services.user_session_manager import UserSessionManager
from llm_services.chat_service_request_manager import ChatServiceRequestManager


###############################################################################################################################################
class UserSessionServer:

    def __init__(
        self,
        user_session_manager: UserSessionManager,
        chat_service_request_manager: ChatServiceRequestManager,
    ) -> None:

        self._user_session_manager: Final[UserSessionManager] = user_session_manager
        self._chat_service_request_manager: Final[ChatServiceRequestManager] = (
            chat_service_request_manager
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
