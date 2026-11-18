from functools import lru_cache
import os
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'AgentOps API'
    environment: str = 'development'
    secret_key: str = 'local-only-change-me-before-deploying'
    access_token_minutes: int = 60 * 24
    database_url: str | None = None
    redis_url: str | None = None
    queue_mode: str = 'local'
    demo_mode: bool = Field(default=False, validation_alias=AliasChoices('AGENTOPS_DEMO_MODE', 'DEMO_MODE'))
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    groq_model: str = 'llama-3.3-70b-versatile'
    gemini_model: str = 'gemini-2.0-flash'
    cost_per_1k_input_tokens: float = 0.0002
    cost_per_1k_output_tokens: float = 0.0008
    cors_origins: str = '*'

    @property
    def effective_database_url(self) -> str:
        if self.demo_mode:
            return 'sqlite:////tmp/agentops-preview.db'
        url = self.database_url or os.getenv('DATABASE_URL')
        if not url:
            return 'sqlite:///./agentops.db'
        if url.startswith('postgres://'):
            return url.replace('postgres://', 'postgresql+psycopg://', 1)
        if url.startswith('postgresql://') and '+psycopg' not in url:
            return url.replace('postgresql://', 'postgresql+psycopg://', 1)
        if url.startswith(('mysql://', 'mysql+pymysql://')):
            raise RuntimeError('AgentOps expects PostgreSQL. The managed Webdev database is MySQL-compatible; configure a PostgreSQL DATABASE_URL or set AGENTOPS_DEMO_MODE=true for the SQLite preview.')
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
