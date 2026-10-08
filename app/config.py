from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RIFTLIKE_", env_file=".env", extra="ignore")

    cors_origin: str = "http://localhost:5180"


@lru_cache
def get_settings() -> Settings:
    return Settings()
