from typing import Final, Annotated, Optional
from langgraph_services.langgraph_service import LanggraphService
from fastapi import Depends
from config.configuration import ChatServerConfig, AnalyzerServerConfig


###############################################################################################################################################
class AppserviceServer:

    def __init__(
        self,
        langgraph_service: LanggraphService,
    ) -> None:

        self._langgraph_service: Final[LanggraphService] = langgraph_service

    ###############################################################################################################################################
    @property
    def langgraph_service(self) -> LanggraphService:
        return self._langgraph_service

    ###############################################################################################################################################


###############################################################################################################################################

_appservice_server_instance: Optional[AppserviceServer] = None


###############################################################################################################################################


def _initialize_langgraph_service() -> LanggraphService:
    chat_server_config = ChatServerConfig()
    analyzer_server_config = AnalyzerServerConfig()
    return LanggraphService(
        chat_service_localhost_urls=[
            f"http://localhost:{chat_server_config.port}{chat_server_config.chat_service_api}"
        ],
        chat_service_test_get_urls=[
            f"http://localhost:{chat_server_config.port}{chat_server_config.test_get_api}"
        ],
        analyzer_service_localhost_urls=[
            f"http://localhost:{analyzer_server_config.port}{analyzer_server_config.analyze_service_api}"
        ],
        analyzer_service_test_get_urls=[
            f"http://localhost:{analyzer_server_config.port}{analyzer_server_config.test_get_api}"
        ],
    )


###############################################################################################################################################
def get_appservice_server_instance() -> AppserviceServer:

    global _appservice_server_instance
    if _appservice_server_instance is None:
        _appservice_server_instance = AppserviceServer(
            langgraph_service=_initialize_langgraph_service(),
        )

    assert (
        _appservice_server_instance is not None
    ), "UserSessionServer instance is not initialized."
    return _appservice_server_instance


###############################################################################################################################################
AppserviceServerInstance = Annotated[
    AppserviceServer, Depends(get_appservice_server_instance)
]
