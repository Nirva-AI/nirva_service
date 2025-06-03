from typing import List, Union
from langchain.schema import AIMessage, HumanMessage, SystemMessage, BaseMessage
from pydantic import BaseModel


############################################################################################################
class LanggraphRequest(BaseModel):
    message: HumanMessage
    chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = []

    class Config:
        arbitrary_types_allowed = True


############################################################################################################
class LanggraphResponse(BaseModel):
    messages: List[BaseMessage] = []

    class Config:
        arbitrary_types_allowed = True


############################################################################################################
