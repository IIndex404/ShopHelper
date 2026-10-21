"""业务任务和系统过场的上下文模型。"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter


class TaskContext(BaseModel):
    flow_id: str
    step_id: str | None = None
    slots: dict = Field(default_factory=dict)


class SystemContext(BaseModel):
    flow_id: str
    step_id: str | None = None


class StartedSystemContext(SystemContext):
    flow_id: Literal["system_task_started"] = "system_task_started"
    started_flow_id: str = ""
    started_flow_name: str = ""


class InterruptedSystemContext(SystemContext):
    flow_id: Literal["system_task_interrupted"] = "system_task_interrupted"
    interrupted_flow_id: str = ""
    interrupted_flow_name: str = ""
    started_flow_id: str = ""
    started_flow_name: str = ""


class CanceledSystemContext(SystemContext):
    flow_id: Literal["system_task_canceled"] = "system_task_canceled"
    canceled_flow_id: str = ""
    canceled_flow_name: str = ""


class ResumedSystemContext(SystemContext):
    flow_id: Literal["system_task_resumed"] = "system_task_resumed"
    resumed_flow_id: str = ""
    resumed_flow_name: str = ""


class CollectedSystemContext(SystemContext):
    flow_id: Literal["system_collect_information"] = "system_collect_information"
    slot_name: str = ""
    response: dict = Field(default_factory=dict)


SystemContextUnion = Annotated[
    StartedSystemContext
    | InterruptedSystemContext
    | CanceledSystemContext
    | ResumedSystemContext
    | CollectedSystemContext,
    Field(discriminator="flow_id"),
]

system_context_adapter = TypeAdapter(SystemContextUnion)
