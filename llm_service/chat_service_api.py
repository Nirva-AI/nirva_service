from typing import List, Union
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel


############################################################################################################
class ChatServiceRequest(BaseModel):
    user_name: str = ""
    input: str = ""
    chat_history: List[Union[SystemMessage, HumanMessage, AIMessage]] = []

    class Config:
        arbitrary_types_allowed = True


############################################################################################################
class ChatServiceResponse(BaseModel):
    user_name: str = ""
    output: str = ""

    class Config:
        arbitrary_types_allowed = True


############################################################################################################
