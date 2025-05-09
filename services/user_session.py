# import datetime
from typing import List, Optional, Union
from llm_serves.chat_system import ChatSystem
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# from typing import Optional
# from game.web_tcg_game import WebTCGGame


class UserSession:

    def __init__(self, user_name: str) -> None:
        self._user_name = user_name
        self._chat_system: Optional[ChatSystem] = None
        # self._game: Optional[WebTCGGame] = None
        # self._last_access_time: datetime.datetime = datetime.datetime.now()

        self._chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = []
        self._chat_history.append(
            SystemMessage(content="你需要扮演一个海盗与我对话，要用海盗的语气哦！")
        )

    ###############################################################################################################################################
    @property
    def chat_system(self) -> Optional[ChatSystem]:
        return self._chat_system

    ###############################################################################################################################################
    @property
    def chat_history(self) -> List[Union[SystemMessage, HumanMessage, AIMessage]]:
        return self._chat_history

    ###############################################################################################################################################
    # @property
    # def game(self) -> Optional[WebTCGGame]:
    #     self._update_access_time()
    #     return self._game

    # ###############################################################################################################################################
    # @game.setter
    # def game(self, game: WebTCGGame) -> None:
    #     self._game = game
    #     self._update_access_time()

    ###############################################################################################################################################
    # def _update_access_time(self) -> None:
    #     self._last_access_time = datetime.datetime.now()

    # ###############################################################################################################################################
    # @property
    # def last_access_time(self) -> datetime.datetime:
    #     return self._last_access_time

    ###############################################################################################################################################
