import json

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.domain.state import DialogueState
from atguigu.models.dialogue_state import DialogueStateRecord


class DialogueStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load_state(self, sender_id: str) -> DialogueState:
        result = await self.session.execute(
            select(DialogueStateRecord).where(
                DialogueStateRecord.sender_id == sender_id
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return DialogueState(sender_id=sender_id)
        return DialogueState.model_validate(json.loads(record.state_json))

    async def save_state(self, state: DialogueState) -> None:
        state_json = json.dumps(
            state.model_dump(mode="json"), ensure_ascii=False
        )
        statement = insert(DialogueStateRecord).values(
            sender_id=state.sender_id,
            state_json=state_json,
        )
        statement = statement.on_duplicate_key_update(
            state_json=statement.inserted.state_json
        )
        await self.session.execute(statement)
        await self.session.commit()
