import asyncio
from collections import OrderedDict

_turn_locks = OrderedDict()

def _turn_lock(sender):
    if sender not in _turn_locks:
        _turn_locks[sender] = asyncio.Lock()
    _turn_locks.move_to_end(sender)
    return _turn_locks[sender]

from atguigu.api.schemas import HistoryMessage
from atguigu.domain.messages import ProcessResult, UserMessage
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.repository.dialogue_state_repository import DialogueStateRepository


class DialogueService:
    def __init__(
        self,
        dialogue_state_repository: DialogueStateRepository,
        dialogue_engine: DialogueEngine,
    ) -> None:
        self.dialogue_state_repository = dialogue_state_repository
        self.dialogue_engine = dialogue_engine

    async def process_message(self, user_message: UserMessage) -> ProcessResult:
        async with _turn_lock(user_message.sender_id):
            state = await self.dialogue_state_repository.load_state(user_message.sender_id)
            result = await self.dialogue_engine.process_message(state, user_message)
            await self.dialogue_state_repository.save_state(state)
            return result

    async def load_chat_history(self, sender_id: str) -> list[HistoryMessage]:
        state = await self.dialogue_state_repository.load_state(sender_id)
        messages: list[HistoryMessage] = []
        for session in state.sessions:
            for turn in session.turns:
                messages.append(
                    HistoryBuilder.to_history_user(
                        session.session_id, turn.user_message
                    )
                )
                messages.extend(
                    HistoryBuilder.to_history_bot(session.session_id, message)
                    for message in turn.bot_messages
                )
        return messages

    async def new_session(self, sender_id: str) -> None:
        async with _turn_lock(sender_id):
            state = await self.dialogue_state_repository.load_state(sender_id)
            state.close_current_session()
            state.reset_runtime_state_for_new_session()
            state.start_session()
            await self.dialogue_state_repository.save_state(state)
