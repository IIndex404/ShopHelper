import asyncio
import json
from abc import ABC, abstractmethod
from urllib.parse import quote

from pydantic import BaseModel

from atguigu.conf.config import settings
from atguigu.domain.state import DialogueState
from atguigu.infrastructure import http_client


class KnowledgeChunk(BaseModel):
    content: str


class KnowledgeProvider(ABC):
    provider_id = ""

    @abstractmethod
    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        raise NotImplementedError


async def _get_data(path: str) -> dict:
    client = http_client.http_client
    if client is None:
        raise RuntimeError("HTTP 客户端尚未初始化")
    response = await client.get(f"{settings.commerce_api_base_url.rstrip('/')}{path}")
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", {})


class ProductAPIProvider(KnowledgeProvider):
    provider_id = "api.product"

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        product_id = quote(state.focused_object.id, safe="")
        data = await _get_data(f"/products/{product_id}")
        return [
            KnowledgeChunk(
                content="商品信息：\n" + json.dumps(data, ensure_ascii=False, indent=2)
            )
        ]


class OrderAPIProvider(KnowledgeProvider):
    provider_id = "api.order"

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        order_id = quote(state.focused_object.id, safe="")
        order, logistics = await asyncio.gather(
            _get_data(f"/orders/{order_id}"),
            _get_data(f"/orders/{order_id}/logistics"),
            return_exceptions=True,
        )
        if isinstance(order, Exception):
            order = {}
        if isinstance(logistics, Exception):
            logistics = {}
        content = {"order_id": state.focused_object.id, "order": order, "logistics": logistics}
        return [
            KnowledgeChunk(
                content="订单与物流信息：\n"
                + json.dumps(content, ensure_ascii=False, indent=2)
            )
        ]


class FAQProvider(KnowledgeProvider):
    provider_id = "faq.default"

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [
            KnowledgeChunk(
                content=(
                    "售后说明：退款申请提交后会进入审核，具体到账时间以原支付渠道为准；"
                    "退货资格与时限以商品页面和平台规则为准；现货通常会尽快安排发货，"
                    "实际时间以订单状态为准。"
                )
            )
        ]


class RAGProvider(KnowledgeProvider):
    provider_id = "rag.default"

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content="知识库暂未配置更多平台规则。")]
