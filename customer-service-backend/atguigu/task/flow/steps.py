"""YAML 流程中的步骤模型。"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from atguigu.task.flow.links import ConditionalLink, FallbackLink, FlowStepLink, StaticLink


class ResponseDefinition(BaseModel):
    mode: str = "static"
    text: str
    prompt: str | None = None


class FlowStepType(str, Enum):
    START = "start"
    END = "end"
    ACTION = "action"
    COLLECT = "collect"


class FlowStep(BaseModel):
    id: str
    type: FlowStepType
    next: list[FlowStepLink] = Field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "FlowStep":
        step_type = step_data.get("type")
        step_class = STEP_TYPE_TO_CLASS.get(step_type)
        if step_class is None:
            raise ValueError(f"未知的流程步骤类型: {step_type!r}")
        return step_class.from_dict(step_data)

    @staticmethod
    def base_fields(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": data["id"],
            "type": FlowStepType(data["type"]),
            "description": data.get("description", ""),
            "next": FlowStep.build_links(data.get("next", [])),
        }

    @staticmethod
    def build_links(data: str | list | None) -> list[FlowStepLink]:
        if data is None:
            return []
        if isinstance(data, str):
            return [StaticLink(target=data)]
        links: list[FlowStepLink] = []
        for item in data:
            if isinstance(item, str):
                links.append(StaticLink(target=item))
            elif "if" in item:
                links.append(ConditionalLink(condition=item["if"], target=item["then"]))
            elif "else" in item:
                links.append(FallbackLink(target=item["else"]))
            else:
                raise ValueError(f"无法识别的流程连接: {item!r}")
        return links


class StartFlowStep(FlowStep):
    type: FlowStepType = FlowStepType.START

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StartFlowStep":
        return cls(**FlowStep.base_fields(data))


class EndFlowStep(FlowStep):
    type: FlowStepType = FlowStepType.END

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EndFlowStep":
        return cls(**FlowStep.base_fields(data))


class ActionFlowStep(FlowStep):
    type: FlowStepType = FlowStepType.ACTION
    action: str
    args: dict | str = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionFlowStep":
        return cls(
            **FlowStep.base_fields(data),
            action=data["action"],
            args=data.get("args", {}),
        )


class CollectFlowStep(FlowStep):
    type: FlowStepType = FlowStepType.COLLECT
    slot_name: str
    response: ResponseDefinition

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CollectFlowStep":
        return cls(
            **FlowStep.base_fields(data),
            slot_name=data["slot_name"],
            response=ResponseDefinition(**data["response"]),
        )


STEP_TYPE_TO_CLASS = {
    "start": StartFlowStep,
    "end": EndFlowStep,
    "action": ActionFlowStep,
    "collect": CollectFlowStep,
}
