from services.user_session_server import UserSessionServer
from fastapi import FastAPI, Depends
from typing import Annotated
from services.user_session_manager import UserSessionManager


###############################################################################################################################################
def initialize_user_session_server_instance(
    server_ip_address: str, server_port: int, local_network_ip: str
) -> UserSessionServer:

    assert UserSessionServer._singleton is None

    if UserSessionServer._singleton is None:
        UserSessionServer._singleton = UserSessionServer(
            fast_api=FastAPI(),
            user_session_manager=UserSessionManager(),
            server_ip_address=server_ip_address,
            server_port=server_port,
            local_network_ip=local_network_ip,
        )

    return UserSessionServer._singleton


###############################################################################################################################################
def get_user_session_server_instance() -> UserSessionServer:
    assert UserSessionServer._singleton is not None
    return UserSessionServer._singleton


###############################################################################################################################################
UserSessionServerInstance = Annotated[
    UserSessionServer, Depends(get_user_session_server_instance)
]
###############################################################################################################################################
