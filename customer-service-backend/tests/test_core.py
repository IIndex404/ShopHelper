import unittest
from unittest.mock import AsyncMock, patch

from atguigu.api.routers.dependencies import get_flows
from atguigu.chitchat.handler import ChitChatHandler
from atguigu.chitchat.responder import ChitChatResponder
from atguigu.clarify.responder import ClarifyResponder
from atguigu.domain.contexts import StartedSystemContext
from atguigu.domain.messages import MessageType, UserMessage
from atguigu.domain.state import DialogueState
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.knowledge.handler import KnowledgeHandler
from atguigu.knowledge.intents import KNOWLEDGE_INTENTS
from atguigu.knowledge.providers import FAQProvider, RAGProvider
from atguigu.knowledge.registry import KnowledgeProviderRegistry
from atguigu.knowledge.responder import KnowledgeResponder
from atguigu.plan.models import TurnPlan
from atguigu.plan.turn_validator import TurnPlanValidator
from atguigu.task.action.builder import build_action_runner
from atguigu.task.command.processor import CommandProcessor
from atguigu.task.flow.executor import FlowExecutor
from atguigu.task.handler import TaskHandler


class FakePlanner:
    def __init__(self, plans: list[TurnPlan]) -> None:
        self.plans = plans

    async def predict(self, state, flows, intents):
        return self.plans.pop(0)


def build_engine(plans: list[TurnPlan]) -> DialogueEngine:
    flows = get_flows()
    return DialogueEngine(
        turn_planner=FakePlanner(plans),
        task_handler=TaskHandler(
            flows=flows,
            command_processor=CommandProcessor(),
            action_runner=build_action_runner(),
            flow_executor=FlowExecutor(),
        ),
        knowledge_handler=KnowledgeHandler(
            knowledge_intents=KNOWLEDGE_INTENTS,
            provider_registry=KnowledgeProviderRegistry([FAQProvider(), RAGProvider()]),
            knowledge_responder=KnowledgeResponder(),
        ),
        chitchat_handler=ChitChatHandler(ChitChatResponder()),
        clarify_responder=ClarifyResponder(),
        turn_plan_validator=TurnPlanValidator(),
    )


def message(number: int, text: str) -> UserMessage:
    return UserMessage(
        sender_id="u1001",
        message_id=f"m{number}",
        type=MessageType.TEXT,
        text=text,
    )


class CoreFlowTests(unittest.IsolatedAsyncioTestCase):
    def test_flow_configuration_is_complete(self):
        flows = get_flows()
        self.assertEqual(9, len(flows.flows))
        for flow in flows.flows:
            self.assertIsNotNone(flow.start_step())

    def test_system_context_survives_json_round_trip(self):
        state = DialogueState(
            sender_id="u1001",
            active_system_task=StartedSystemContext(
                step_id="start",
                started_flow_id="refund_request",
                started_flow_name="退款申请",
            ),
        )
        restored = DialogueState.model_validate_json(state.model_dump_json())
        self.assertIsInstance(restored.active_system_task, StartedSystemContext)
        self.assertEqual("退款申请", restored.active_system_task.started_flow_name)

    async def test_refund_flow_from_start_to_finish(self):
        plans = [
            TurnPlan.from_dict(
                {"task": {"commands": [{"command": "start_flow", "flow": "refund_request"}]}}
            ),
            TurnPlan.from_dict(
                {"task": {"commands": [{"command": "set_slots", "slots": {"order_number": "A20260410001"}}]}}
            ),
            TurnPlan.from_dict(
                {"task": {"commands": [{"command": "set_slots", "slots": {"refund_reason": "尺码不合适"}}]}}
            ),
        ]
        engine = build_engine(plans)
        state = DialogueState(sender_id="u1001")

        first = await engine.process_message(state, message(1, "我要退款"))
        self.assertEqual(2, len(first.messages))
        self.assertIn("退款申请", first.messages[0].text)
        self.assertIn("订单号", first.messages[1].text)

        second = await engine.process_message(state, message(2, "A20260410001"))
        self.assertIn("退款原因", second.messages[0].text)

        with patch('atguigu.task.action.custom.refund.call_api', new=AsyncMock(return_value={
            'eligible': True, 'applications': []})):
            third = await engine.process_message(state, message(3, "尺码不合适"))
        self.assertIn("A20260410001", third.messages[0].text)
        self.assertIn("尺码不合适", third.messages[0].text)
        self.assertIsNone(state.active_task)
        self.assertIsNotNone(state.pending_refund)
        with patch('atguigu.task.action.custom.refund.call_api', new=AsyncMock(return_value={
            'request_id': state.pending_refund['request_id'], 'status': 'submitted'})) as api:
            result = await engine.process_message(state, message(4, '确认提交'))
        self.assertIn('申请编号', result.messages[0].text)
        self.assertEqual('POST', api.call_args.args[2])
        self.assertIsNone(state.pending_refund)
        self.assertEqual(4, len(state.current_session().turns))


if __name__ == "__main__":
    unittest.main()
