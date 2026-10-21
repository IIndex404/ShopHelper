from enum import Enum

from pydantic import BaseModel, Field

from atguigu.task.command.models import Command


class TaskTurnPlan(BaseModel):
    commands: list[Command] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskTurnPlan":
        return cls(
            commands=[Command.from_dict(item) for item in data.get("commands", [])]
        )


class KnowledgeTurnPlan(BaseModel):
    intents: list[str] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeTurnPlan":
        return cls(intents=data.get("intents", []))


class ChitchatTurnPlan(BaseModel):
    pass


class TurnPlan(BaseModel):
    task: TaskTurnPlan | None = None
    knowledge: KnowledgeTurnPlan | None = None
    chitchat: ChitchatTurnPlan | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "TurnPlan":
        if not isinstance(data, dict):
            raise ValueError("TurnPlan 必须是 JSON 对象")
        return cls(
            task=TaskTurnPlan.from_dict(data["task"])
            if data.get("task") is not None
            else None,
            knowledge=KnowledgeTurnPlan.from_dict(data["knowledge"])
            if data.get("knowledge") is not None
            else None,
            chitchat=ChitchatTurnPlan()
            if data.get("chitchat") is not None
            else None,
        )


class ClarifyReason(str, Enum):
    MISSING_TRACK = "missing_track"
    MULTIPLE_TRACKS = "multiple_tracks"
    MISSING_TASK_COMMANDS = "missing_task_commands"
    MISSING_KNOWLEDGE_INTENT = "missing_knowledge_intent"
    UNKNOWN_KNOWLEDGE_INTENT = "unknown_knowledge_intent"
    MISSING_FOCUSED_OBJECT = "missing_focused_object"
    OBJECT_REQUIRES_INTENT = "object_requires_intent"
    INVALID_TASK_COMMANDS = "invalid_task_commands"
    MULTIPLE_TASK_FLOWS = "multiple_task_flows"
    UNKNOWN_TASK_FLOW = "unknown_task_flow"


class TurnPlanValidationResult(BaseModel):
    valid: bool
    reason: ClarifyReason | None = None
