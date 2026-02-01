from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./mafia_ace.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Providers
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    CARTESIA_API_KEY: str = ""

    # Voice (Pipecat)
    DEEPGRAM_API_KEY: str = ""
    DAILY_API_KEY: str = ""

    # Weave
    WANDB_API_KEY: str = ""
    WEAVE_ENTITY: str = "williamacallahan-william-a-callahan-cfa"
    WEAVE_PROJECT: str = "mafia-ace"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Game defaults
    DEFAULT_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 2

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
