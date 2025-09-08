from datetime import datetime
from typing import final

from pydantic import BaseModel, Field

from .registry import register_base_model_class


@final
@register_base_model_class
class SessionContext(BaseModel):
    """User session context for storing locale and timezone information"""
    
    username: str = Field(
        description="Username of the user"
    )
    timezone: str = Field(
        default="UTC",
        description="User's timezone (e.g., 'America/Los_Angeles', 'Asia/Shanghai')"
    )
    locale: str = Field(
        default="en-US", 
        description="User's locale (e.g., 'en-US', 'zh-CN')"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp in UTC"
    )