from typing import final, List
from pydantic import BaseModel
from .registry import register_base_model_class
from .prompt import EventAnalysis, DailyReflection


@final
@register_base_model_class
class JournalFile(BaseModel):
    username: str
    time_stamp: str
    events: List[EventAnalysis]
    daily_reflection: DailyReflection
