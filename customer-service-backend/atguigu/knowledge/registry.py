from atguigu.knowledge.providers import KnowledgeProvider


class KnowledgeProviderRegistry:
    def __init__(self, providers: list[KnowledgeProvider]) -> None:
        self._providers_by_id = {provider.provider_id: provider for provider in providers}

    def get(self, provider_id: str) -> KnowledgeProvider:
        try:
            return self._providers_by_id[provider_id]
        except KeyError as exc:
            raise KeyError(f"未知知识提供者: {provider_id}") from exc
