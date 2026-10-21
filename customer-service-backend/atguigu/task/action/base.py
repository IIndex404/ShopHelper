"""Action 插件接口。"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState


class ActionResult(BaseModel):
    messages: list[BotMessage] = Field(default_factory=list)
    slot_updates: dict[str, Any] = Field(default_factory=dict)


class Action(ABC):
    name: str

    @abstractmethod
    async def run(
        self, state: DialogueState, action_kwargs: dict[str, Any]
    ) -> ActionResult:
        raise NotImplementedError
