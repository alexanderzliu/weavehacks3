from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./mafia_ace.db"

    # AI Providers
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    )
    CARTESIA_API_KEY: str = ""

    # OpenAI-compatible endpoint (Groq, Together, Ollama, etc.)
    OPENAI_COMPATIBLE_BASE_URL: str = ""
    OPENAI_COMPATIBLE_API_KEY: str = ""
    OPENAI_COMPATIBLE_MODEL: str = "gpt-4o-mini"

    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"

    # Default models for direct providers
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    GOOGLE_MODEL: str = "gemini-2.0-flash"

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
        env_file = ("../.env", ".env")  # Check parent dir first, then local
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
