from typing import List, Union
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


class UserSession:

    def __init__(self, user_name: str) -> None:
        self._user_name = user_name
        self._chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = []
        self._chat_history.append(
            SystemMessage(content="你需要扮演一个海盗与我对话，要用海盗的语气哦！")
        )

    ###############################################################################################################################################
    @property
    def chat_history(self) -> List[Union[SystemMessage, HumanMessage, AIMessage]]:
        return self._chat_history

    ###############################################################################################################################################
