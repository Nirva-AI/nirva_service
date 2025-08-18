from enum import IntEnum
from typing import List, Optional, TYPE_CHECKING, final

from pydantic import BaseModel, Field

from .registry import register_base_model_class

if TYPE_CHECKING:
    from .prompt import EventAnalysis

################################################################################################################
################################################################################################################
################################################################################################################


@final
@register_base_model_class
class URLConfigurationResponse(BaseModel):
    api_version: str = ""
    endpoints: dict[str, str] = {}
    deprecated: bool = False
    notice: str = ""


################################################################################################################
################################################################################################################
################################################################################################################


@final
class MessageRole(IntEnum):
    SYSTEM = 0
    HUMAN = 1
    AI = 2


@final
@register_base_model_class
class ChatMessage(BaseModel):
    id: str
    role: MessageRole
    content: str
    time_stamp: str
    tags: Optional[List[str]] = None


@final
@register_base_model_class
class ChatActionRequest(BaseModel):
    human_message: ChatMessage
    chat_history: List[ChatMessage]


@final
@register_base_model_class
class ChatActionResponse(BaseModel):
    ai_message: ChatMessage


################################################################################################################
################################################################################################################
################################################################################################################


@final
@register_base_model_class
class AnalyzeActionRequest(BaseModel):
    time_stamp: str
    file_number: int


################################################################################################################
################################################################################################################
################################################################################################################


@final
@register_base_model_class
class UploadTranscriptActionRequest(BaseModel):
    transcript_content: str
    time_stamp: str
    file_number: int
    file_suffix: str


@final
@register_base_model_class
class UploadTranscriptActionResponse(BaseModel):
    message: str = ""


################################################################################################################
################################################################################################################
################################################################################################################


@final
@register_base_model_class
class BackgroundTaskResponse(BaseModel):
    task_id: str
    message: str


###################################################################################################################################################################


@final
@register_base_model_class
class IncrementalAnalyzeRequest(BaseModel):
    """增量分析请求"""
    time_stamp: str = Field(description="日期时间戳 (e.g., '2025-04-19')")
    new_transcript: str = Field(description="新的转录内容")


@final
@register_base_model_class
class IncrementalAnalyzeResponse(BaseModel):
    """增量分析响应"""
    updated_events_count: int = Field(description="更新的事件数量")
    new_events_count: int = Field(description="新增的事件数量")
    total_events_count: int = Field(description="总事件数量")
    message: str = Field(description="处理结果消息")


@final
@register_base_model_class
class GetEventsRequest(BaseModel):
    """获取事件列表请求"""
    time_stamp: str = Field(description="日期时间戳 (e.g., '2025-04-19')")


@final
@register_base_model_class
class GetEventsResponse(BaseModel):
    """获取事件列表响应"""
    time_stamp: str = Field(description="日期时间戳")
    events: List["EventAnalysis"] = Field(description="事件列表")
    total_count: int = Field(description="事件总数")
    last_updated: str = Field(description="最后更新时间")


###################################################################################################################################################################
