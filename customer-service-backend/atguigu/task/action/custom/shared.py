"""访问配套电商服务的通用函数。"""

from urllib.parse import quote

from atguigu.conf.config import settings
from atguigu.infrastructure import http_client


def _base_url() -> str:
    return settings.commerce_api_base_url.rstrip("/")


async def _request_data(path: str) -> dict | None:
    client = http_client.http_client
    if client is None:
        return None
    try:
        response = await client.get(f"{_base_url()}{path}")
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else None
    except Exception:
        return None


async def fetch_order(order_id: str) -> dict | None:
    return await _request_data(f"/orders/{quote(order_id, safe='')}")


async def fetch_logistics(order_id: str) -> dict | None:
    return await _request_data(
        f"/orders/{quote(order_id, safe='')}/logistics"
    )


async def fetch_product(product_id: str) -> dict | None:
    return await _request_data(f"/products/{quote(product_id, safe='')}")
