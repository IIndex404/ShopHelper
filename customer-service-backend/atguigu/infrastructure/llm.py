"""按配置初始化兼容 OpenAI 协议的聊天模型。"""

from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model

from atguigu.conf.config import settings


def _build_llm() -> BaseChatModel | None:
    key = settings.llm_api_key.strip()
    if not key or key.lower() in {"your key", "your-key", "changeme"}:
        return None
    return init_chat_model(
        model=settings.llm_model,
        model_provider="openai",
        api_key=key,
        base_url=settings.llm_base_url,
        temperature=0,
        timeout=12,
        max_retries=0,
    )


llm = _build_llm()
