from typing import Final, Optional, cast, final

import httpx
import requests
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger

from .langgraph_models import (
    LanggraphRequest,
    LanggraphResponse,
    RequestTaskMessageListType,
)


@final
class LanggraphRequestTask:
    ################################################################################################################################################################################
    def __init__(
        self,
        username: str,
        prompt: str,
        chat_history: RequestTaskMessageListType,
        timeout: Optional[int] = None,
    ) -> None:
        self._prompt: Final[str] = prompt
        self._chat_history: RequestTaskMessageListType = chat_history
        self._response: LanggraphResponse = LanggraphResponse()
        self._username: str = username
        self._timeout: Final[int] = timeout if timeout is not None else 30

        for message in self._chat_history:
            if not isinstance(message, (SystemMessage, HumanMessage, AIMessage)):
                assert (
                    False
                ), f"Invalid message type: {type(message)}. Expected SystemMessage, HumanMessage, or AIMessage."

    ################################################################################################################################################################################
    @property
    def last_response_message_content(self) -> str:
        if len(self._response.messages) == 0:
            # logger.warning(f"{self._username} response is empty.")
            return ""
        return cast(str, self._response.messages[-1].content)

    ################################################################################################################################################################################
    def request(self, url: str) -> None:
        try:
            logger.debug(f"{self._username} request prompt:\n{self._prompt}")

            response = requests.post(
                url=url,
                json=LanggraphRequest(
                    message=HumanMessage(content=self._prompt, name=self._username),
                    chat_history=self._chat_history,
                ).model_dump(),
                timeout=self._timeout,
            )

            if response.status_code == 200:
                self._response = LanggraphResponse.model_validate(response.json())
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
                json=LanggraphRequest(
                    message=HumanMessage(content=self._prompt, name=self._username),
                    chat_history=self._chat_history,
                ).model_dump(),
                timeout=self._timeout,
            )

            if response.status_code == 200:
                self._response = LanggraphResponse.model_validate(response.json())
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
