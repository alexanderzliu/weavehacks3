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


# [CC1b] Registry pattern replaces type switch (>3 cases)
_PROVIDER_REGISTRY: dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        default_model="gpt-4o",
        api_key_env="OPENAI_API_KEY",
    ),
    "ollama": ProviderConfig(
        default_model="llama3.2",
        api_key_env="OLLAMA_API_KEY",
        base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/v1",
        api_key_placeholder="ollama",
    ),
    "together": ProviderConfig(
        default_model="meta-llama/Llama-3-70b-chat-hf",
        api_key_env="TOGETHER_API_KEY",
        base_url="https://api.together.xyz/v1",
    ),
    "groq": ProviderConfig(
        default_model="llama-3.1-70b-versatile",
        api_key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
    ),
}


def create_llm_provider(
    provider: str = "openai",
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> BaseChatModel:
    """Create a LangChain chat model.

    Args:
        provider: Provider name (openai, ollama, together, groq, or openai-compatible)
        model: Model name to use
        api_key: API key (falls back to environment variable)
        base_url: Base URL for OpenAI-compatible endpoints

    Returns:
        BaseChatModel instance

    Raises:
        ValueError: If provider is unknown or openai-compatible without base_url
    """
    # Handle openai-compatible separately (requires base_url)
    if provider == "openai-compatible":
        if not base_url:
            raise ValueError("base_url required for openai-compatible provider")
        return ChatOpenAI(
            api_key=SecretStr(api_key or ""),  # type: ignore[call-arg]
            model=model or "gpt-4o",  # type: ignore[call-arg]
            base_url=base_url,  # type: ignore[call-arg]
        )

    # Lookup in registry
    config = _PROVIDER_REGISTRY.get(provider)
    if not config:
        raise ValueError(f"Unknown provider: {provider}")

    # Resolve API key
    resolved_key = api_key or config.api_key_placeholder or os.getenv(config.api_key_env, "")

    return ChatOpenAI(
        api_key=SecretStr(resolved_key),  # type: ignore[call-arg]
        model=model or config.default_model,  # type: ignore[call-arg]
        base_url=base_url or config.base_url,  # type: ignore[call-arg]
    )
