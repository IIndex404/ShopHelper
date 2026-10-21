import time
from atguigu.conf.config import settings
from atguigu.domain.messages import ProcessResult, BotMessage
from atguigu.plan.models import ClarifyReason
from atguigu.task.action.custom.refund import submit_pending

class DialogueEngine:
    def __init__(self, turn_planner, task_handler, knowledge_handler, chitchat_handler,
                 clarify_responder, turn_plan_validator):
        self.turn_planner = turn_planner
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler
        self.clarify_responder = clarify_responder
        self.turn_plan_validator = turn_plan_validator

    async def process_message(self, state, message):
        session = state.current_session()
        # A repeated network request replays the stored result, without executing tools again.
        if session:
            for turn in session.turns:
                if turn.user_message.message_id == message.message_id:
                    return ProcessResult(sender_id=state.sender_id, message_id=message.message_id,
                                         messages=turn.bot_messages)
            if time.time() - session.last_activity_at > settings.session_timeout_seconds:
                state.close_current_session()
                state.reset_runtime_state_for_new_session()
                state.pending_refund = None
        state.begin_turn(message)
        if message.object:
            if state.pending_refund and message.object.type == 'order' and message.object.id != state.pending_refund['order_id']:
                state.pending_refund = None
            state.set_focused_object(message.object)
        raw = (message.text or '').strip()
        if state.pending_refund and raw in {'取消', '取消退款', '算了', '不办了'}:
            state.pending_refund = None
            messages = [BotMessage(text='已取消待确认的退款申请，没有提交。')]
        elif state.pending_refund and raw == '确认提交':
            messages = await submit_pending(state)
        elif state.pending_refund and not state.pending_refund.get('attempted') and raw.startswith('修改原因：'):
            reason = raw.split('：', 1)[1].strip()
            if 2 <= len(reason) <= 255:
                state.pending_refund['reason'] = reason
                messages = [BotMessage(text=f'退款原因已改为：{reason}。回复“确认提交”正式提交，或回复“取消”。', suggestions=['确认提交', '取消'])]
            else:
                messages = [BotMessage(text='退款原因请填写 2 到 255 个字。')]
        else:
            plan = await self.turn_planner.predict(state, self.task_handler.flows,
                                                   self.knowledge_handler.knowledge_intents)
            checked = self.turn_plan_validator.validate(plan, self.task_handler.flows, state,
                                                        self.knowledge_handler.knowledge_intents)
            if not checked.valid:
                messages = await self.clarify_responder.respond(state, checked.reason)
            elif message.object and not message.text and plan.chitchat is not None:
                messages = await self.clarify_responder.respond(state, ClarifyReason.OBJECT_REQUIRES_INTENT)
            elif plan.task is not None:
                messages = await self.task_handler.handle(plan.task.commands, state)
            elif plan.knowledge is not None:
                messages = await self.knowledge_handler.handle(plan.knowledge.intents, state)
            elif state.pending_refund:
                from atguigu.task.action.custom.refund import confirmation_reminder
                messages = [BotMessage(text=confirmation_reminder(state), suggestions=['确认提交', '取消'])]
            else:
                messages = await self.chitchat_handler.handle(state)
        state.pending_turn.bot_messages = messages
        state.commit_turn()
        return ProcessResult(sender_id=state.sender_id, message_id=message.message_id, messages=messages)
