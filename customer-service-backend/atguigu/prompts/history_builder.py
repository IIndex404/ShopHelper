"""把领域消息转换为 Prompt 文本或 API 历史消息。"""

import json

from atguigu.api.schemas import ChatObject, HistoryMessage
from atguigu.domain.messages import BotMessage, FocusedObject, MessageType, UserMessage
from atguigu.domain.state import Turn


class HistoryBuilder:
    @staticmethod
    def build(turns: list[Turn]) -> str:
        lines: list[str] = []
        for turn in turns:
            lines.append(f"USER: {HistoryBuilder.render_user_message(turn.user_message)}")
            lines.extend(
                f"BOT: {HistoryBuilder.render_bot_message(message)}"
                for message in turn.bot_messages
            )
        return "\n".join(lines)

    @staticmethod
    def render_user_message(message: UserMessage) -> str:
        if message.type is MessageType.TEXT:
            return (message.text or "").strip()
        return HistoryBuilder._render_object(message.object)

    @staticmethod
    def render_bot_message(message: BotMessage) -> str:
        if message.text:
            return message.text.strip()
        return HistoryBuilder._render_object(message.object)

    @staticmethod
    def _render_object(obj: FocusedObject | None) -> str:
        if obj is None:
            return "[空对象]"
        label = "订单对象" if obj.type == "order" else "商品对象"
        attributes = json.dumps(obj.attributes, ensure_ascii=False)
        return f"[label={label}, id={obj.id}, title={obj.title}, attributes={attributes}]"

    @staticmethod
    def to_history_user(session_id: str, message: UserMessage) -> HistoryMessage:
        return HistoryMessage(
            session_id=session_id,
            role="user",
            text=message.text,
            object=ChatObject(**message.object.model_dump()) if message.object else None,
        )

    @staticmethod
    def to_history_bot(session_id: str, message: BotMessage) -> HistoryMessage:
        return HistoryMessage(
            session_id=session_id,
            role="bot",
            suggestions=message.suggestions,
            text=message.text,
            object=ChatObject(**message.object.model_dump()) if message.object else None,
        )
