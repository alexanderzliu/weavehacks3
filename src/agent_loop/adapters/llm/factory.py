"""LLM Provider factory.

Creates LangChain chat models based on configuration.
Uses ChatOpenAI for all OpenAI-compatible endpoints.

Sources:
    - ChatOpenAI: https://python.langchain.com/docs/integrations/chat/openai/
"""

import os
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for an LLM provider."""

    default_model: str
    api_key_env: str
    base_url: str | None = None
    api_key_placeholder: str | None = None  # For providers that don't need real keys
    detection_env: str | None = None  # Env var to check for auto-detection
    detection_priority: int = 100  # Lower = higher priority for auto-detection


# [CC1b] Registry pattern replaces type switch (>3 cases)
_PROVIDER_REGISTRY: dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        default_model="gpt-4o",
        api_key_env="OPENAI_API_KEY",
        detection_env="OPENAI_API_KEY",
        detection_priority=20,
    ),
    "ollama": ProviderConfig(
        default_model="llama3.2",
        api_key_env="OLLAMA_API_KEY",
        base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/v1",
        api_key_placeholder="ollama",
        detection_env="OLLAMA_HOST",
        detection_priority=50,
    ),
    "together": ProviderConfig(
        default_model="meta-llama/Llama-3-70b-chat-hf",
        api_key_env="TOGETHER_API_KEY",
        base_url="https://api.together.xyz/v1",
        detection_env="TOGETHER_API_KEY",
        detection_priority=40,
    ),
    "groq": ProviderConfig(
        default_model="llama-3.1-70b-versatile",
        api_key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
        detection_env="GROQ_API_KEY",
        detection_priority=30,
    ),
    "openai-compatible": ProviderConfig(
        default_model=os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-4o"),
        api_key_env="OPENAI_COMPATIBLE_API_KEY",
        base_url=os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
        detection_env="OPENAI_COMPATIBLE_BASE_URL",
        detection_priority=10,  # Highest priority (explicit custom endpoint)
    ),
}


def _detect_default_provider() -> str:
    """Auto-detect provider based on available environment variables.

    Uses detection_priority from registry (lower = higher priority).
    """
    # Sort by priority, filter to those with detection_env set and present
    candidates = [
        (name, config)
        for name, config in _PROVIDER_REGISTRY.items()
        if config.detection_env and os.getenv(config.detection_env)
    ]
    if candidates:
        # Sort by priority and return highest priority (lowest number)
        candidates.sort(key=lambda x: x[1].detection_priority)
        return candidates[0][0]
    return "openai"  # Fall back to openai (will fail if no key)


def create_llm_provider(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> BaseChatModel:
    """Create a LangChain chat model.

    Args:
        provider: Provider name (openai, ollama, together, groq, openai-compatible).
                  If None, auto-detects based on environment variables.
        model: Model name to use
        api_key: API key (falls back to environment variable)
        base_url: Base URL for OpenAI-compatible endpoints

    Returns:
        BaseChatModel instance

    Raises:
        ValueError: If provider is unknown or openai-compatible without base_url
    """
    # Auto-detect provider if not specified
    resolved_provider = provider or _detect_default_provider()

    # Lookup in registry
    config = _PROVIDER_REGISTRY.get(resolved_provider)
    if not config:
        raise ValueError(f"Unknown provider: {resolved_provider}")

    # Validate base_url for openai-compatible
    resolved_base_url = base_url or config.base_url
    if resolved_provider == "openai-compatible" and not resolved_base_url:
        raise ValueError("base_url required for openai-compatible provider")

    # Resolve API key
    resolved_key = api_key or config.api_key_placeholder or os.getenv(config.api_key_env, "")

    return ChatOpenAI(
        api_key=SecretStr(resolved_key),  # type: ignore[call-arg]
        model=model or config.default_model,  # type: ignore[call-arg]
        base_url=resolved_base_url,  # type: ignore[call-arg]
    )
