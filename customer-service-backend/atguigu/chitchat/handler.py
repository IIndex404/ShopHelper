from atguigu.chitchat.responder import ChitChatResponder
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState


class ChitChatHandler:
    def __init__(self, responder: ChitChatResponder) -> None:
        self.responder = responder

    async def handle(self, state: DialogueState) -> list[BotMessage]:
        session = state.current_session()
        return await self.responder.respond(
            user_message=state.pending_turn.user_message,
            recent_turns=session.turns if session else [],
        )
