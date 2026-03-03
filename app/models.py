from datetime import datetime
from pydantic import BaseModel, Field


class RawMessage(BaseModel):
    group_name: str
    sender: str
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StructuredEvent(BaseModel):
    id: int | None = None
    group_name: str
    sender: str
    message_text: str
    category: str
    location_from: str | None = None
    location_to: str | None = None
    capability: str
    urgency: int = Field(default=1, ge=1, le=5)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    supporting_events: list[StructuredEvent]
