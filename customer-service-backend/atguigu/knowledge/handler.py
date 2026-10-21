from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.knowledge.providers import KnowledgeChunk
from atguigu.knowledge.registry import KnowledgeProviderRegistry
from atguigu.knowledge.responder import KnowledgeResponder


class KnowledgeHandler:
    def __init__(
        self,
        knowledge_intents: dict[str, KnowledgeIntent],
        provider_registry: KnowledgeProviderRegistry,
        knowledge_responder: KnowledgeResponder,
    ) -> None:
        self.knowledge_intents = knowledge_intents
        self.provider_registry = provider_registry
        self.knowledge_responder = knowledge_responder

    async def handle(
        self, intents: list[str], state: DialogueState
    ) -> list[BotMessage]:
        chunks: list[KnowledgeChunk] = []
        for provider_id in self._get_provider_ids_by_intents(intents):
            try:
                chunks.extend(await self.provider_registry.get(provider_id).retrieve(state))
            except Exception as exc:
                chunks.append(KnowledgeChunk(content=f"{provider_id} 暂时不可用：{exc}"))
        session = state.current_session()
        return await self.knowledge_responder.respond(
            user_message=state.pending_turn.user_message,
            recent_turns=session.turns if session else [],
            chunks=chunks,
        )

    def _get_provider_ids_by_intents(self, intents: list[str]) -> list[str]:
        result: list[str] = []
        for intent in intents:
            for provider_id in self.knowledge_intents[intent].provider_ids:
                if provider_id not in result:
                    result.append(provider_id)
        return result
