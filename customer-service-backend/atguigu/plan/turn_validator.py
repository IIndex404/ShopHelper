from atguigu.domain.state import DialogueState
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.plan.models import ClarifyReason, TurnPlan, TurnPlanValidationResult
from atguigu.task.command.models import (
    CancelFlowCommand,
    ResumeFlowCommand,
    SetSlotsCommand,
    StartFlowCommand,
)
from atguigu.task.flow.flows import FlowsList


class TurnPlanValidator:
    def validate(
        self,
        plan: TurnPlan,
        flows: FlowsList,
        state: DialogueState,
        intents: dict[str, KnowledgeIntent],
    ) -> TurnPlanValidationResult:
        tracks = [
            name
            for name in ("task", "knowledge", "chitchat")
            if getattr(plan, name) is not None
        ]
        if not tracks:
            return self._reject(ClarifyReason.MISSING_TRACK)
        if len(tracks) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TRACKS)
        if tracks[0] == "task":
            return self._validate_task(plan, flows)
        if tracks[0] == "knowledge":
            return self._validate_knowledge(plan, state, intents)
        return TurnPlanValidationResult(valid=True)

    @staticmethod
    def _reject(reason: ClarifyReason) -> TurnPlanValidationResult:
        return TurnPlanValidationResult(valid=False, reason=reason)

    def _validate_task(
        self, plan: TurnPlan, flows: FlowsList
    ) -> TurnPlanValidationResult:
        commands = plan.task.commands
        if not commands:
            return self._reject(ClarifyReason.MISSING_TASK_COMMANDS)
        allowed = (
            StartFlowCommand,
            ResumeFlowCommand,
            CancelFlowCommand,
            SetSlotsCommand,
        )
        if not all(isinstance(command, allowed) for command in commands):
            return self._reject(ClarifyReason.INVALID_TASK_COMMANDS)
        starts = [command for command in commands if isinstance(command, StartFlowCommand)]
        if len(starts) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TASK_FLOWS)
        if starts and flows.get_flow_by_id(starts[0].flow) is None:
            return self._reject(ClarifyReason.UNKNOWN_TASK_FLOW)
        return TurnPlanValidationResult(valid=True)

    def _validate_knowledge(
        self,
        plan: TurnPlan,
        state: DialogueState,
        intents: dict[str, KnowledgeIntent],
    ) -> TurnPlanValidationResult:
        requested = plan.knowledge.intents
        if not requested:
            return self._reject(ClarifyReason.MISSING_KNOWLEDGE_INTENT)
        for name in requested:
            meta = intents.get(name)
            if meta is None:
                return self._reject(ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT)
            if meta.requires_object and (
                state.focused_object is None
                or state.focused_object.type != meta.requires_object
            ):
                return self._reject(ClarifyReason.MISSING_FOCUSED_OBJECT)
        return TurnPlanValidationResult(valid=True)
