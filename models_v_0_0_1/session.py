from typing import final, List
from pydantic import BaseModel
from .registry import register_base_model_class
from langchain_core.messages import BaseMessage


@final
@register_base_model_class
class UserSession(BaseModel):
    username: str
    chat_history: List[BaseMessage]
    update_at: str
