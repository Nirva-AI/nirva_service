from typing import final, List
from pydantic import BaseModel
from .registry import register_base_model_class
from langchain_core.messages import BaseMessage


@final
@register_base_model_class
class UserSession(BaseModel):
    """用户会话数据模型，包含用户名和聊天历史"""

    user_name: str
    chat_history: List[BaseMessage] = []
