"""推进系统流程和业务流程，直到需要等待用户输入。"""

import ast

from atguigu.domain.contexts import CollectedSystemContext
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import ActionResult
from atguigu.task.action.runner import ActionCall, ActionRunner
from atguigu.task.flow.flows import FlowsList
from atguigu.task.flow.links import ConditionalLink, FallbackLink, StaticLink
from atguigu.task.flow.steps import (
    ActionFlowStep,
    CollectFlowStep,
    EndFlowStep,
    FlowStep,
    StartFlowStep,
)


class FlowExecutor:
    async def run_task(
        self, state: DialogueState, flows: FlowsList, action_runner: ActionRunner
    ) -> list[BotMessage]:
        messages: list[BotMessage] = []
        for _ in range(100):
            action_call = self.advance_until_action(state, flows)
            if action_call.action_name == "action_listen":
                return messages
            result: ActionResult = await action_runner.run(action_call, state)
            if result.slot_updates:
                state.set_slots(result.slot_updates)
            messages.extend(result.messages)
        raise RuntimeError("流程执行超过 100 个 Action，可能存在死循环")

    def advance_until_action(
        self, state: DialogueState, flows: FlowsList
    ) -> ActionCall:
        for _ in range(100):
            context = state.current_active_task()
            if context is None:
                return ActionCall(action_name="action_listen")
            flow = flows.get_flow_by_id(context.flow_id)
            if flow is None:
                raise ValueError(f"找不到当前流程: {context.flow_id}")
            step = flow.get_step_by_id(context.step_id)
            if step is None:
                raise ValueError(f"流程 {flow.id} 找不到步骤: {context.step_id}")
            action_call = self._run_step(state, step, flows)
            if action_call is not None:
                return action_call
        raise RuntimeError("流程节点推进超过 100 次，可能存在死循环")

    def _run_step(
        self, state: DialogueState, step: FlowStep, flows: FlowsList
    ) -> ActionCall | None:
        if isinstance(step, StartFlowStep):
            self._advance_next_step(state, step)
            return None
        if isinstance(step, EndFlowStep):
            if state.active_system_task is not None:
                state.end_active_system_task()
            else:
                state.end_active_task()
            return None
        if isinstance(step, CollectFlowStep):
            return self._run_collect_step(step, state, flows)
        if isinstance(step, ActionFlowStep):
            self._advance_next_step(state, step)
            return self._build_action_call(state, step)
        raise TypeError(f"不支持的流程步骤: {type(step).__name__}")

    def _advance_next_step(self, state: DialogueState, step: FlowStep) -> None:
        next_step_id = self._select_next_step(step, state)
        if next_step_id is None:
            raise ValueError(f"步骤 {step.id} 没有可用的下一步")
        context = state.current_active_task()
        if context is None:
            raise RuntimeError("推进步骤时没有活动上下文")
        context.step_id = next_step_id

    def _select_next_step(
        self, step: FlowStep, state: DialogueState
    ) -> str | None:
        fallback: str | None = None
        for link in step.next:
            if isinstance(link, StaticLink):
                return link.target
            if isinstance(link, ConditionalLink) and self._eval_condition(
                state, link.condition
            ):
                return link.target
            if isinstance(link, FallbackLink):
                fallback = link.target
        return fallback

    @staticmethod
    def _eval_condition(state: DialogueState, condition: str) -> bool:
        tree = ast.parse(condition, mode="eval")
        allowed = (
            ast.Expression,
            ast.BoolOp,
            ast.And,
            ast.Or,
            ast.UnaryOp,
            ast.Not,
            ast.Compare,
            ast.Eq,
            ast.NotEq,
            ast.Gt,
            ast.GtE,
            ast.Lt,
            ast.LtE,
            ast.In,
            ast.NotIn,
            ast.Name,
            ast.Load,
            ast.Constant,
            ast.List,
            ast.Tuple,
            ast.Dict,
            ast.Subscript,
            ast.Call,
            ast.Attribute,
        )
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                raise ValueError(f"条件表达式包含不允许的语法: {type(node).__name__}")
            if isinstance(node, ast.Name) and node.id not in {"slots", "context"}:
                raise ValueError(f"条件表达式不能访问变量: {node.id}")
            if isinstance(node, ast.Attribute):
                if node.attr != "get" or not isinstance(node.value, ast.Name):
                    raise ValueError("条件表达式只允许对 slots/context 调用 get")
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
                    raise ValueError("条件表达式只允许调用 get")
        context = state.current_active_task()
        return bool(
            eval(
                compile(tree, "<flow-condition>", "eval"),
                {"__builtins__": {}},
                {
                    "slots": state.active_task.slots if state.active_task else {},
                    "context": context.model_dump(mode="json") if context else {},
                },
            )
        )

    @staticmethod
    def _build_action_call(state: DialogueState, step: ActionFlowStep) -> ActionCall:
        kwargs = step.args
        if isinstance(kwargs, str):
            context = state.active_system_task
            if context is None:
                raise ValueError(f"{step.id} 的参数 {kwargs} 需要系统上下文")
            _, field = kwargs.split(".", 1)
            kwargs = context.model_dump(mode="json").get(field, {})
        return ActionCall(action_name=step.action, action_kwargs=kwargs)

    def _run_collect_step(
        self, step: CollectFlowStep, state: DialogueState, flows: FlowsList
    ) -> ActionCall | None:
        self._try_to_fill_collect_slot_focused_object(state, step)
        if state.active_task and state.active_task.slots.get(step.slot_name):
            self._advance_next_step(state, step)
            return None
        system_flow = flows.get_flow_by_id("system_collect_information")
        if system_flow is None or system_flow.start_step() is None:
            raise ValueError("缺少 system_collect_information 系统流程")
        state.start_active_system_task(
            CollectedSystemContext(
                step_id=system_flow.start_step().id,
                slot_name=step.slot_name,
                response=step.response.model_dump(mode="json"),
            )
        )
        return None

    @staticmethod
    def _try_to_fill_collect_slot_focused_object(
        state: DialogueState, step: CollectFlowStep
    ) -> None:
        focused = state.focused_object
        if focused is None:
            return
        if step.slot_name == "order_number" and focused.type == "order":
            state.set_slots({step.slot_name: focused.id})
        elif step.slot_name == "product_id" and focused.type == "product":
            state.set_slots({step.slot_name: focused.id})
