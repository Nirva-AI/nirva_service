from user_services.user_session_server import UserSessionServer
from fastapi import Depends
from typing import Annotated
from user_services.user_session_manager import UserSessionManager


###############################################################################################################################################
def initialize_user_session_server_instance() -> UserSessionServer:

    assert UserSessionServer._singleton is None

    if UserSessionServer._singleton is None:
        UserSessionServer._singleton = UserSessionServer(
            user_session_manager=UserSessionManager(),
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
