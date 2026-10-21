"""对话消息领域模型。"""

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class FocusedObject(BaseModel):
    """用户在页面上选中的订单或商品。"""

    id: str
    type: str
    title: str | None = None
    attributes: dict = Field(default_factory=dict)


class MessageType(str, Enum):
    TEXT = "text"
    OBJECT = "object"


class UserMessage(BaseModel):
    sender_id: str
    message_id: str
    type: MessageType
    text: str | None = None
    object: FocusedObject | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "UserMessage":
        if self.type is MessageType.TEXT and not (self.text or "").strip():
            raise ValueError("文本消息必须包含 text")
        if self.type is MessageType.OBJECT and self.object is None:
            raise ValueError("对象消息必须包含 object")
        return self


class BotMessage(BaseModel):
    suggestions: list[str] = Field(default_factory=list)
    text: str | None = None
    object: FocusedObject | None = None


class ProcessResult(BaseModel):
    sender_id: str
    message_id: str
    messages: list[BotMessage] = Field(default_factory=list)
