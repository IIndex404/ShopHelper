"""LLM 规划结果中允许出现的命令。"""

from typing import Any

from pydantic import BaseModel, Field


class Command(BaseModel):
    command: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Command":
        name = data.get("command")
        command_class = COMMAND_NAME_TO_CLASS.get(name)
        if command_class is None:
            raise ValueError(f"未知命令: {name!r}")
        return command_class(**data)


class StartFlowCommand(Command):
    flow: str


class SetSlotsCommand(Command):
    slots: dict[str, Any] = Field(default_factory=dict)


class CancelFlowCommand(Command):
    pass


class ResumeFlowCommand(Command):
    flow: str | None = None


COMMAND_NAME_TO_CLASS = {
    "start_flow": StartFlowCommand,
    "set_slots": SetSlotsCommand,
    "cancel_flow": CancelFlowCommand,
    "resume_flow": ResumeFlowCommand,
}
