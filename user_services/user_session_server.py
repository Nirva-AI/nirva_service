from typing import Optional, Final
from user_services.user_session_manager import UserSessionManager


###############################################################################################################################################
class UserSessionServer:

    _singleton: Optional["UserSessionServer"] = None

    def __init__(
        self,
        user_session_manager: UserSessionManager,
    ) -> None:

        self._user_session_manager: Final[UserSessionManager] = user_session_manager

    ###############################################################################################################################################
    @property
    def user_session_manager(self) -> UserSessionManager:
        return self._user_session_manager

    ###############################################################################################################################################
