from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.infrastructure.llm import llm
from atguigu.plan.models import ClarifyReason
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.loader import load_prompt


class ClarifyResponder:
    async def respond(
        self, state: DialogueState, reason: ClarifyReason
    ) -> list[BotMessage]:
        base = self.build_clarify_message(reason, state)
        if llm is None:
            return [BotMessage(text=base)]
        try:
            session = state.current_session()
            prompt = PromptTemplate.from_template(
                load_prompt("clarify_respond"), template_format="jinja2"
            )
            answer = await (prompt | llm | StrOutputParser()).ainvoke(
                {
                    "reason": reason.value,
                    "clarify_message": base,
                    "user_message": HistoryBuilder.render_user_message(
                        state.pending_turn.user_message
                    ),
                    "history": HistoryBuilder.build(session.turns[-10:] if session else []),
                    "focused_object": state.focused_object.model_dump_json()
                    if state.focused_object
                    else None,
                }
            )
            return [BotMessage(text=answer)]
        except Exception:
            return [BotMessage(text=base)]

    @staticmethod
    def build_clarify_message(
        reason: ClarifyReason, state: DialogueState
    ) -> str:
        messages = {
            ClarifyReason.MULTIPLE_TRACKS: "你这次提到了多个方向，想先办业务还是先咨询信息？",
            ClarifyReason.MISSING_FOCUSED_OBJECT: "请先发送你想咨询的订单或商品，我再继续帮你看。",
            ClarifyReason.MISSING_KNOWLEDGE_INTENT: "你想了解商品、订单，还是售后配送规则？",
            ClarifyReason.MISSING_TRACK: "你想办理业务，还是咨询信息？",
            ClarifyReason.MISSING_TASK_COMMANDS: "你想查订单、查物流，还是申请退款？",
        }
        if reason in messages:
            return messages[reason]
        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            if state.focused_object and state.focused_object.type == "order":
                return "我收到了这个订单。你想查状态、查物流，还是申请退款？"
            if state.focused_object and state.focused_object.type == "product":
                return "我收到了这个商品。你想了解价格、规格，还是售后信息？"
        return "我还没完全明白你的意思，可以再具体说一下吗？"
