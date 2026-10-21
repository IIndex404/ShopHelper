"""完整流程与槽位集合。"""

from pydantic import BaseModel, Field

from atguigu.task.flow.steps import FlowStep, StartFlowStep


class FlowSlot(BaseModel):
    name: str
    type: str = "any"
    label: str = ""
    description: str = ""


class Flow(BaseModel):
    id: str
    name: str | None = None
    description: str = ""
    steps: list[FlowStep] = Field(default_factory=list)
    slots: list[FlowSlot] = Field(default_factory=list)

    def start_step(self) -> StartFlowStep | None:
        return next((step for step in self.steps if isinstance(step, StartFlowStep)), None)

    def get_step_by_id(self, step_id: str | None) -> FlowStep | None:
        return next((step for step in self.steps if step.id == step_id), None)


class FlowsList(BaseModel):
    flows: list[Flow] = Field(default_factory=list)
    slots: dict[str, FlowSlot] = Field(default_factory=dict)

    def get_flow_by_id(self, flow_id: str) -> Flow | None:
        return next((flow for flow in self.flows if flow.id == flow_id), None)
