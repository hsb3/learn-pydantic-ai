from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DURAGRAPH_")

    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    task_queue: str = "agents"
    redis_url: str = "redis://localhost:6379/0"

    # In prod these come from Key Vault via Managed Identity, not env.
    default_model: str = "openai:gpt-4o"


@lru_cache
def get_settings() -> Settings:
    return Settings()
