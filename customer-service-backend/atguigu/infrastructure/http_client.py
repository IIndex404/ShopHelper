import httpx


http_client: httpx.AsyncClient | None = None


def init_http_client() -> None:
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=10.0)


async def close_http_client() -> None:
    global http_client
    if http_client is not None:
        await http_client.aclose()
    http_client = None
