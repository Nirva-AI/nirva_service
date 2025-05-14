from loguru import logger
from typing import List, Union, Optional, Final, final
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import httpx
from llm_services.chat_service_api import (
    ChatServiceRequest,
    ChatServiceResponse,
)
import requests


@final
class ChatServiceRequestHandler:

    ################################################################################################################################################################################
    def __init__(
        self,
        user_name: str,
        prompt: str,
        chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]],
    ) -> None:

        self._prompt: Final[str] = prompt
        self._chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = (
            chat_history
        )
        self._response: Optional[ChatServiceResponse] = None
        self._user_name: str = user_name
        self._timeout: Final[int] = 30

    ################################################################################################################################################################################
    @property
    def response_content(self) -> str:
        if self._response is None:
            return ""
        return self._response.output

    ################################################################################################################################################################################
    def request(self, url: str) -> Optional[ChatServiceResponse]:

        assert self._response is None
        assert url != ""

        if self._prompt == "" or url == "":
            logger.error(f"{self._user_name}: request error: prompt or url is empty")
            return None

        try:

            logger.debug(f"{self._user_name} request prompt:\n{self._prompt}")

            response = requests.post(
                url=url,
                json=ChatServiceRequest(
                    user_name=self._user_name,
                    input=self._prompt,
                    chat_history=self._chat_history,
                ).model_dump(),
                timeout=self._timeout,
            )

            if response.status_code == 200:
                self._response = ChatServiceResponse.model_validate(response.json())
                logger.info(
                    f"{self._user_name} request-response:\n{self._response.model_dump_json()}"
                )
            else:
                logger.error(
                    f"request-response Error: {response.status_code}, {response.text}"
                )

        except Exception as e:
            logger.error(f"{self._user_name}: request error: {e}")

        return self._response

    ################################################################################################################################################################################
    async def a_request(
        self, client: httpx.AsyncClient, url: str
    ) -> Optional[ChatServiceResponse]:

        assert self._response is None
        assert url != ""

        if self._prompt == "" or url == "":
            logger.error(f"{self._user_name}: a_request error: prompt or url is empty")
            return None

        try:

            logger.debug(f"{self._user_name} a_request prompt:\n{self._prompt}")

            response = await client.post(
                url=url,
                json=ChatServiceRequest(
                    user_name=self._user_name,
                    input=self._prompt,
                    chat_history=self._chat_history,
                ).model_dump(),
                timeout=self._timeout,
            )

            if response.status_code == 200:
                self._response = ChatServiceResponse.model_validate(response.json())
                logger.info(
                    f"{self._user_name} a_request-response:\n{self._response.model_dump_json()}"
                )
            else:
                logger.error(
                    f"a_request-response Error: {response.status_code}, {response.text}"
                )

        except Exception as e:
            logger.error(f"{self._user_name}: a_request error: {e}")

        return self._response

    ################################################################################################################################################################################
