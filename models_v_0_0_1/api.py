# import datetime
from typing import final
from pydantic import BaseModel
from .registry import register_base_model_class
from .prompt import LabelExtractionResponse, ReflectionResponse
from datetime import datetime

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
@register_base_model_class
class ChatActionRequest(BaseModel):
    content: str = ""


@final
@register_base_model_class
class ChatActionResponse(BaseModel):
    message: str = ""


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
