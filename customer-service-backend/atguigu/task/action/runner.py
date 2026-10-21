from typing import Any

from pydantic import BaseModel, Field

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import ActionResult
from atguigu.task.action.registry import ActionRegistry


class ActionCall(BaseModel):
    action_name: str
    action_kwargs: dict[str, Any] = Field(default_factory=dict)


class ActionRunner:
    def __init__(self, registry: ActionRegistry) -> None:
        self.registry = registry

    async def run(self, action_call: ActionCall, state: DialogueState) -> ActionResult:
        return await self.registry.get(action_call.action_name).run(
            state, action_call.action_kwargs
        )
