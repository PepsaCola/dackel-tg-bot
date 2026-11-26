from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FeedbackType(StrEnum):
    FEEDBACK = "feedback"
    COMPLAINT = "complaint"
    BUG = "bug"
    SUGGESTION = "suggestion"


class Platform(StrEnum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    OTHER = "other"


class FeedbackIn(BaseModel):
    """Тіло запиту, яке надсилає застосунок."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    type: FeedbackType
    message: str = Field(min_length=3, max_length=3000)
    rating: int | None = Field(default=None, ge=1, le=5)
    user_id: str | None = Field(default=None, max_length=64)
    contact: str | None = Field(default=None, max_length=128)
    platform: Platform | None = None
    app_version: str | None = Field(default=None, max_length=32)
    locale: str | None = Field(default=None, max_length=16)


class FeedbackAccepted(BaseModel):
    id: str
    status: Literal["accepted"] = "accepted"