from typing import Optional, Dict
from services.user_session import UserSession


class UserSessionManager:

    def __init__(self) -> None:
        self._user_sessions: Dict[str, UserSession] = {}

    ###############################################################################################################################################
    def has_user_session(self, user_name: str) -> bool:
        return user_name in self._user_sessions

    ###############################################################################################################################################
    def get_user_session(self, user_name: str) -> Optional[UserSession]:
        return self._user_sessions.get(user_name, None)

    ###############################################################################################################################################
    def create_user_session(self, user_name: str) -> UserSession:
        if self.has_user_session(user_name):
            assert False, f"user_session {user_name} already exists"
        new_user_session = UserSession(user_name)
        self._user_sessions[user_name] = new_user_session
        return new_user_session

    ###############################################################################################################################################
    def remove_user_session(self, user_session: UserSession) -> None:
        user_name = user_session._user_name
        assert user_name in self._user_sessions
        self._user_sessions.pop(user_name, None)

    ###############################################################################################################################################
