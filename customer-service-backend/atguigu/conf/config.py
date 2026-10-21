"""集中读取环境配置。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    llm_model: str = "qwen-plus"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str = ""
    commerce_api_base_url: str = "http://127.0.0.1:18081"
    database_url: str = (
        "mysql+asyncmy://root:123456@127.0.0.1:3306/customer_service?charset=utf8mb4"
    )
    database_url_sync: str = (
        "mysql+pymysql://root:123456@127.0.0.1:3306/customer_service?charset=utf8mb4"
    )
    app_host: str = "127.0.0.1"
    app_port: int = 18082
    session_timeout_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
