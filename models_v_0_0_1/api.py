# import datetime
from typing import Optional, final, List
from pydantic import BaseModel
from .registry import register_base_model_class
from .prompt import LabelExtractionResponse, ReflectionResponse
from datetime import datetime
from enum import IntEnum

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
    role: int  # MessageRole 0: system, 1: human, 2: ai
    content: str
    time_stamp: str
    tags: Optional[List[str]] = None


@final
@register_base_model_class
class ChatActionRequest(BaseModel):
    human_message: ChatMessage
    chat_history: List[ChatMessage] = []


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
    time_stamp: datetime = datetime.now()
    file_number: int = 0

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


@final
@register_base_model_class
class AnalyzeActionResponse(BaseModel):
    label_extraction: LabelExtractionResponse | None = None
    reflection: ReflectionResponse | None = None
    message: str = ""


################################################################################################################
################################################################################################################
################################################################################################################


@final
@register_base_model_class
class UploadTranscriptActionRequest(BaseModel):
    transcript_content: str = ""
    time_stamp: datetime = datetime.now()
    file_number: int = 0
    file_suffix: str = "txt"

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


@final
@register_base_model_class
class UploadTranscriptActionResponse(BaseModel):
    message: str = ""


################################################################################################################
################################################################################################################
################################################################################################################
