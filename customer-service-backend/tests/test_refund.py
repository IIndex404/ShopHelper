import time
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from atguigu.domain.state import DialogueState
from atguigu.domain.contexts import TaskContext
from atguigu.task.action.custom.refund import PrepareRefundAction, submit_pending, LookupRefundAction
from test_core import build_engine, message

class RefundTests(unittest.IsolatedAsyncioTestCase):
    def state(self):
        return DialogueState(sender_id='u1001', active_task=TaskContext(
            flow_id='refund_request', step_id='refund_submitted',
            slots={'order_number': 'A20260410001', 'refund_reason': '不再需要'}))

    async def prepare(self, state, data=None):
        with patch('atguigu.task.action.custom.refund.call_api', new=AsyncMock(return_value=data or {
            'eligible': True, 'applications': []})) as api:
            result = await PrepareRefundAction().run(state, {})
        self.assertEqual(1, api.call_count)
        self.assertEqual(2, len(api.call_args.args))  # GET only, no submission
        return result

    async def test_preview_never_submits(self):
        state = self.state()
        result = await self.prepare(state)
        self.assertIn('确认提交', result.messages[0].text)
        self.assertIsNotNone(state.pending_refund)

    async def test_duplicate_existing_is_not_submitted(self):
        state = self.state()
        result = await self.prepare(state, {'eligible': True, 'applications': [
            {'request_id': 'R12345678', 'status': 'submitted', 'status_desc': '等待审核'}]})
        self.assertIsNone(state.pending_refund)
        self.assertIn('未重复提交', result.messages[0].text)

    async def test_cancelled_order_blocked(self):
        state = self.state()
        result = await self.prepare(state, {'eligible': False, 'eligibility_reason': '已取消订单不支持申请'})
        self.assertIsNone(state.pending_refund)
        self.assertIn('不支持', result.messages[0].text)

    async def test_expired_confirmation_does_not_post(self):
        state = self.state()
        await self.prepare(state)
        state.pending_refund['created_at'] = time.time() - 601
        with patch('atguigu.task.action.custom.refund.call_api', new=AsyncMock()) as api:
            result = await submit_pending(state)
        api.assert_not_called()
        self.assertIn('10 分钟', result[0].text)

    async def test_timeout_reuses_identical_request_id(self):
        state = self.state()
        await self.prepare(state)
        request_id = state.pending_refund['request_id']
        with patch('atguigu.task.action.custom.refund.call_api', new=AsyncMock(side_effect=httpx.ReadTimeout('timeout'))):
            result = await submit_pending(state)
        self.assertIn('无法确认', result[0].text)
        with patch('atguigu.task.action.custom.refund.call_api', new=AsyncMock(return_value={
            'status': 'submitted', 'request_id': request_id})) as api:
            await submit_pending(state)
        self.assertEqual(request_id, api.call_args.args[3]['request_id'])
        self.assertIsNone(state.pending_refund)

    async def test_raw_cancel_never_calls_business_api(self):
        state = self.state()
        await self.prepare(state)
        engine = build_engine([])
        with patch('atguigu.task.action.custom.refund.call_api', new=AsyncMock()) as api:
            result = await engine.process_message(state, message(1, '取消'))
        api.assert_not_called()
        self.assertIn('没有提交', result.messages[0].text)
        self.assertIsNone(state.pending_refund)

    async def test_same_message_replays_without_tools(self):
        state = self.state()
        await self.prepare(state)
        engine = build_engine([])
        state.pending_refund['request_id'] = 'R12345678'
        with patch('atguigu.task.action.custom.refund.call_api', new=AsyncMock(return_value={
            'status': 'submitted', 'request_id': 'R12345678'})) as api:
            first = await engine.process_message(state, message(1, '确认提交'))
            replay = await engine.process_message(state, message(1, '确认提交'))
        self.assertEqual(first, replay)
        self.assertEqual(1, api.call_count)

    async def test_unavailable_query_never_claims_no_records(self):
        with patch('atguigu.task.action.custom.refund.call_api', new=AsyncMock(side_effect=httpx.ConnectError('offline'))):
            result = await LookupRefundAction().run(self.state(), {})
        self.assertIn('查询失败', result.messages[0].text)

    async def test_change_reason_requires_reconfirmation(self):
        state = self.state()
        await self.prepare(state)
        engine = build_engine([])
        result = await engine.process_message(state, message(1, '修改原因：尺寸不合适'))
        self.assertEqual('尺寸不合适', state.pending_refund['reason'])
        self.assertIn('确认提交', result.messages[0].text)


class PlannerRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_longer_needed_is_reason_not_cancellation(self):
        from atguigu.plan.turn_planner import TurnPlanner
        from atguigu.api.routers.dependencies import get_flows
        from atguigu.knowledge.intents import KNOWLEDGE_INTENTS
        state = DialogueState(sender_id='u1001', active_task=TaskContext(
            flow_id='refund_request', step_id='ask_refund_reason', slots={'order_number': 'A123456'}))
        state.begin_turn(message(1, '重复下单，不再需要'))
        plan = await TurnPlanner().predict(state, get_flows(), KNOWLEDGE_INTENTS)
        self.assertEqual('set_slots', plan.task.commands[0].command)
        self.assertEqual('重复下单，不再需要', plan.task.commands[0].slots['refund_reason'])

    async def test_refund_success_question_queries_status(self):
        from atguigu.plan.turn_planner import TurnPlanner
        from atguigu.api.routers.dependencies import get_flows
        from atguigu.knowledge.intents import KNOWLEDGE_INTENTS
        state = DialogueState(sender_id='u1001')
        state.begin_turn(message(1, '退款成功了吗'))
        plan = await TurnPlanner().predict(state, get_flows(), KNOWLEDGE_INTENTS)
        self.assertEqual('refund_status_query', plan.task.commands[0].flow)

    async def test_reason_containing_cancel_is_still_reason(self):
        from atguigu.plan.turn_planner import TurnPlanner
        from atguigu.api.routers.dependencies import get_flows
        from atguigu.knowledge.intents import KNOWLEDGE_INTENTS
        state = DialogueState(sender_id='u1001', active_task=TaskContext(
            flow_id='refund_request', step_id='ask_refund_reason', slots={'order_number': 'A123456'}))
        state.begin_turn(message(1, '买错了，需要取消重复购买'))
        plan = await TurnPlanner().predict(state, get_flows(), KNOWLEDGE_INTENTS)
        self.assertEqual('set_slots', plan.task.commands[0].command)


    async def test_model_omitting_explicit_order_gets_bound(self):
        from langchain_core.runnables import RunnableLambda
        from atguigu.plan.turn_planner import TurnPlanner
        from atguigu.api.routers.dependencies import get_flows
        from atguigu.knowledge.intents import KNOWLEDGE_INTENTS
        state = DialogueState(sender_id='u1001')
        state.begin_turn(message(1, '我要给订单 A20260410001 申请退款'))
        model = RunnableLambda(lambda value: '{"task":{"commands":[{"command":"start_flow","flow":"refund_request"}]}}')
        with patch('atguigu.plan.turn_planner.llm', model):
            plan = await TurnPlanner().predict(state, get_flows(), KNOWLEDGE_INTENTS)
        self.assertEqual('A20260410001', plan.task.commands[-1].slots['order_number'])

    async def test_new_conversation_clears_confirmation_without_deleting_history(self):
        from atguigu.service.dialogue_service import DialogueService
        state = DialogueState(sender_id='u1001', pending_refund={'order_id':'A123456'})
        state.begin_turn(message(1, '历史消息'))
        state.commit_turn()
        repository = AsyncMock()
        repository.load_state.return_value = state
        await DialogueService(repository, None).new_session('u1001')
        self.assertIsNone(state.pending_refund)
        self.assertEqual(2, len(state.sessions))
        self.assertEqual(1, len(state.sessions[0].turns))
        repository.save_state.assert_awaited_once()


    def test_collected_order_is_retained_as_conversation_context(self):
        from atguigu.task.command.processor import CommandProcessor
        from atguigu.task.command.models import SetSlotsCommand
        from atguigu.api.routers.dependencies import get_flows
        state = DialogueState(sender_id='u1001', active_task=TaskContext(
            flow_id='refund_request', step_id='ask_order_number'))
        CommandProcessor().run([SetSlotsCommand(command='set_slots', slots={'order_number':'A20260410001'})], state, get_flows())
        state.end_active_task()
        self.assertEqual('A20260410001', state.focused_object.id)
        self.assertEqual('order', state.focused_object.type)
