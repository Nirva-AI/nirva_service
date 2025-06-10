from typing import Optional, final, List
from pydantic import BaseModel
from .registry import register_base_model_class
from enum import IntEnum
from .journal import JournalFile

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


# @final
# @register_base_model_class
# class AnalyzeActionResponse(BaseModel):
#     journal_file: JournalFile


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
