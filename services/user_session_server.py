from typing import Optional, Final
from services.user_session_manager import UserSessionManager
from fastapi import FastAPI
import os


###############################################################################################################################################
class UserSessionServer:

    _singleton: Optional["UserSessionServer"] = None

    def __init__(
        self,
        fast_api: FastAPI,
        user_session_manager: UserSessionManager,
        server_ip_address: str,
        server_port: int,
        local_network_ip: str,
    ) -> None:

        self._fast_api: Final[FastAPI] = fast_api
        self._user_session_manager: Final[UserSessionManager] = user_session_manager
        self._server_ip_address: Final[str] = server_ip_address
        self._server_port: Final[int] = server_port
        self._local_network_ip: Final[str] = local_network_ip

    ###############################################################################################################################################
    @property
    def user_session_manager(self) -> UserSessionManager:
        return self._user_session_manager

    ###############################################################################################################################################
    @property
    def server_ip_address(self) -> str:
        return self._server_ip_address

    ###############################################################################################################################################
    @property
    def server_port(self) -> int:
        return self._server_port

    ###############################################################################################################################################
    @property
    def local_network_ip(self) -> str:
        return self._local_network_ip

    ###############################################################################################################################################
    @property
    def fast_api(self) -> FastAPI:
        return self._fast_api

    ###############################################################################################################################################
    @property
    def pid(self) -> int:
        return os.getpid()

    ###############################################################################################################################################
