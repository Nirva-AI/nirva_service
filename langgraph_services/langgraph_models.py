from typing import List, Union, final
from langchain.schema import AIMessage, HumanMessage, SystemMessage, BaseMessage
from pydantic import BaseModel


RequestTaskMessageType = List[SystemMessage | HumanMessage | AIMessage]


############################################################################################################
@final
class LanggraphRequest(BaseModel):
    message: HumanMessage
    chat_history: RequestTaskMessageType = []

    class Config:
        arbitrary_types_allowed = True


############################################################################################################
@final
class LanggraphResponse(BaseModel):
    messages: List[BaseMessage] = []

    class Config:
        arbitrary_types_allowed = True


############################################################################################################
