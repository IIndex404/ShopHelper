"""把计划命令应用到 DialogueState。"""

from atguigu.domain.contexts import (
    CanceledSystemContext,
    InterruptedSystemContext,
    ResumedSystemContext,
    StartedSystemContext,
    TaskContext,
)
from atguigu.domain.state import DialogueState
from atguigu.domain.messages import FocusedObject
from atguigu.task.command.models import (
    CancelFlowCommand,
    Command,
    ResumeFlowCommand,
    SetSlotsCommand,
    StartFlowCommand,
)
from atguigu.task.flow.flows import FlowsList


class CommandProcessor:
    def run(self, commands: list[Command], state: DialogueState, flows: FlowsList) -> None:
        for command in commands:
            self._apply(command, state, flows)

    def _apply(self, command: Command, state: DialogueState, flows: FlowsList) -> None:
        if isinstance(command, StartFlowCommand):
            self._handle_start_flow(command, state, flows)
        elif isinstance(command, SetSlotsCommand):
            self._handle_set_slots(command, state)
        elif isinstance(command, CancelFlowCommand):
            self._handle_cancel_flow(state, flows)
        elif isinstance(command, ResumeFlowCommand):
            self._handle_resume_flow(command, state, flows)
        else:
            raise ValueError(f"不支持的命令类型: {type(command).__name__}")

    @staticmethod
    def _readable_flow_name(flow_id: str, flows: FlowsList) -> str:
        flow = flows.get_flow_by_id(flow_id)
        return flow.name or flow_id if flow else flow_id

    @staticmethod
    def _system_start_step(flows: FlowsList, flow_id: str) -> str:
        flow = flows.get_flow_by_id(flow_id)
        if flow is None or flow.start_step() is None:
            raise ValueError(f"系统流程 {flow_id} 不存在或没有 start")
        return flow.start_step().id

    def _activate_started(
        self, state: DialogueState, flows: FlowsList, flow_id: str
    ) -> None:
        state.start_active_system_task(
            StartedSystemContext(
                step_id=self._system_start_step(flows, "system_task_started"),
                started_flow_id=flow_id,
                started_flow_name=self._readable_flow_name(flow_id, flows),
            )
        )

    def _activate_interrupted(
        self,
        state: DialogueState,
        flows: FlowsList,
        interrupted_flow_id: str,
        started_flow_id: str,
    ) -> None:
        state.start_active_system_task(
            InterruptedSystemContext(
                step_id=self._system_start_step(flows, "system_task_interrupted"),
                interrupted_flow_id=interrupted_flow_id,
                interrupted_flow_name=self._readable_flow_name(interrupted_flow_id, flows),
                started_flow_id=started_flow_id,
                started_flow_name=self._readable_flow_name(started_flow_id, flows),
            )
        )

    def _activate_resumed(
        self, state: DialogueState, flows: FlowsList, flow_id: str
    ) -> None:
        state.start_active_system_task(
            ResumedSystemContext(
                step_id=self._system_start_step(flows, "system_task_resumed"),
                resumed_flow_id=flow_id,
                resumed_flow_name=self._readable_flow_name(flow_id, flows),
            )
        )

    def _activate_canceled(
        self, state: DialogueState, flows: FlowsList, flow_id: str
    ) -> None:
        state.start_active_system_task(
            CanceledSystemContext(
                step_id=self._system_start_step(flows, "system_task_canceled"),
                canceled_flow_id=flow_id,
                canceled_flow_name=self._readable_flow_name(flow_id, flows),
            )
        )

    def _handle_start_flow(
        self, command: StartFlowCommand, state: DialogueState, flows: FlowsList
    ) -> None:
        state.end_active_system_task()
        if command.flow.startswith("system_"):
            raise ValueError("不能从用户命令直接启动系统流程")
        target = flows.get_flow_by_id(command.flow)
        if target is None or target.start_step() is None:
            raise ValueError(f"未知或不完整的流程: {command.flow}")

        current = state.active_task
        if current is not None:
            if current.flow_id == command.flow:
                return
            interrupted_id = current.flow_id
            state.interrupted_active_task()
            if not state.resumed_active_task(command.flow):
                state.start_active_task(
                    TaskContext(flow_id=command.flow, step_id=target.start_step().id)
                )
            self._activate_interrupted(state, flows, interrupted_id, command.flow)
            return

        if state.resumed_active_task(command.flow):
            self._activate_resumed(state, flows, command.flow)
            return

        state.start_active_task(
            TaskContext(flow_id=command.flow, step_id=target.start_step().id)
        )
        self._activate_started(state, flows, command.flow)

    @staticmethod
    def _handle_set_slots(command: SetSlotsCommand, state: DialogueState) -> None:
        state.set_slots(command.slots)
        order = command.slots.get('order_number')
        if isinstance(order, str) and order.strip():
            state.set_focused_object(FocusedObject(type='order', id=order.strip()))

    def _handle_cancel_flow(self, state: DialogueState, flows: FlowsList) -> None:
        current = state.active_task
        if current is None:
            return
        canceled_id = current.flow_id
        state.cancel_active_task()
        self._activate_canceled(state, flows, canceled_id)

    def _handle_resume_flow(
        self, command: ResumeFlowCommand, state: DialogueState, flows: FlowsList
    ) -> None:
        if command.flow is not None:
            if flows.get_flow_by_id(command.flow) is None:
                raise ValueError(f"未知流程: {command.flow}")
            target_id = command.flow
        else:
            if not state.paused_tasks:
                return
            target_id = state.paused_tasks[-1].flow_id

        current = state.active_task
        if current is not None:
            if current.flow_id == target_id:
                return
            interrupted_id = current.flow_id
            state.interrupted_active_task()
            if not state.resumed_active_task(target_id):
                state.resumed_active_task(interrupted_id)
                return
            self._activate_interrupted(state, flows, interrupted_id, target_id)
            return

        if state.resumed_active_task(target_id):
            self._activate_resumed(state, flows, target_id)
