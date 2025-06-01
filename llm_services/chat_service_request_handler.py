from loguru import logger
from typing import List, Union, Final, final, cast
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
        username: str,
        prompt: str,
        chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]],
    ) -> None:

        self._prompt: Final[str] = prompt
        self._chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = (
            chat_history
        )
        self._response: ChatServiceResponse = ChatServiceResponse()
        self._username: str = username
        self._timeout: Final[int] = 30

    ################################################################################################################################################################################
    @property
    def response_output(self) -> str:
        if len(self._response.messages) == 0:
            logger.warning(f"{self._username} response is empty.")
            return ""
        return cast(str, self._response.messages[-1].content)

    ################################################################################################################################################################################
    def request(self, url: str) -> None:

        try:

            logger.debug(f"{self._username} request prompt:\n{self._prompt}")

            response = requests.post(
                url=url,
                json=ChatServiceRequest(
                    message=HumanMessage(content=self._prompt, name=self._username),
                    chat_history=self._chat_history,
                ).model_dump(),
                timeout=self._timeout,
            )

            if response.status_code == 200:
                self._response = ChatServiceResponse.model_validate(response.json())
                logger.info(
                    f"{self._username} request-response:\n{self._response.model_dump_json()}"
                )
            else:
                logger.error(
                    f"request-response Error: {response.status_code}, {response.text}"
                )

        except Exception as e:
            logger.error(f"{self._username}: request error: {e}")

    ################################################################################################################################################################################
    async def a_request(self, client: httpx.AsyncClient, url: str) -> None:

        try:

            logger.debug(f"{self._username} a_request prompt:\n{self._prompt}")

            response = await client.post(
                url=url,
                json=ChatServiceRequest(
                    message=HumanMessage(content=self._prompt, name=self._username),
                    chat_history=self._chat_history,
                ).model_dump(),
                timeout=self._timeout,
            )

            if response.status_code == 200:
                self._response = ChatServiceResponse.model_validate(response.json())
                logger.info(
                    f"{self._username} a_request-response:\n{self._response.model_dump_json()}"
                )
            else:
                logger.error(
                    f"a_request-response Error: {response.status_code}, {response.text}"
                )

        except Exception as e:
            logger.error(f"{self._username}: a_request error: {e}")

    ################################################################################################################################################################################
