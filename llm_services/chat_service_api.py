from typing import List, Union
from langchain.schema import AIMessage, HumanMessage, SystemMessage, BaseMessage
from pydantic import BaseModel


############################################################################################################
class ChatServiceRequest(BaseModel):
    message: HumanMessage
    chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = []

    class Config:
        arbitrary_types_allowed = True


############################################################################################################
class ChatServiceResponse(BaseModel):
    messages: List[BaseMessage] = []

    class Config:
        arbitrary_types_allowed = True


############################################################################################################
