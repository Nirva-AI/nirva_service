from typing import List, final

from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

RequestTaskMessageListType = List[SystemMessage | HumanMessage | AIMessage]


############################################################################################################
@final
class LanggraphRequest(BaseModel):
    message: HumanMessage
    chat_history: RequestTaskMessageListType = []

    class Config:
        arbitrary_types_allowed = True


############################################################################################################
@final
class LanggraphResponse(BaseModel):
    messages: List[BaseMessage] = []

    class Config:
        arbitrary_types_allowed = True


############################################################################################################
