from pydantic import BaseModel, Field, model_validator


class ChatObject(BaseModel):
    type: str
    id: str
    title: str | None = None
    attributes: dict = Field(default_factory=dict)


class ChatRequest(BaseModel):
    sender_id: str
    message_id: str | None = None
    text: str | None = None
    object: ChatObject | None = None

    @model_validator(mode="after")
    def require_content(self) -> "ChatRequest":
        if not (self.text or "").strip() and self.object is None:
            raise ValueError("text 和 object 至少传一个")
        return self


class ChatBotMessage(BaseModel):
    suggestions: list[str] = Field(default_factory=list)
    text: str | None = None
    object: ChatObject | None = None


class ChatResponse(BaseModel):
    sender_id: str
    message_id: str
    messages: list[ChatBotMessage] = Field(default_factory=list)


class HistoryMessage(BaseModel):
    suggestions: list[str] = Field(default_factory=list)
    session_id: str
    role: str
    text: str | None = None
    object: ChatObject | None = None


class HistoryResponse(BaseModel):
    sender_id: str
    messages: list[HistoryMessage] = Field(default_factory=list)
