"""LLM Provider factory.

Creates LangChain chat models based on configuration.
Uses ChatOpenAI for all OpenAI-compatible endpoints.

Sources:
    - ChatOpenAI: https://python.langchain.com/docs/integrations/chat/openai/
"""

import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


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
    """
    if provider == "openai":
        return ChatOpenAI(
            api_key=SecretStr(api_key or os.getenv("OPENAI_API_KEY", "")),
            model=model or "gpt-4o",
        )

    elif provider == "ollama":
        return ChatOpenAI(
            api_key=SecretStr("ollama"),  # Not used but required
            model=model or "llama3.2",
            base_url=base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/v1",
        )

    elif provider == "together":
        return ChatOpenAI(
            api_key=SecretStr(api_key or os.getenv("TOGETHER_API_KEY", "")),
            model=model or "meta-llama/Llama-3-70b-chat-hf",
            base_url="https://api.together.xyz/v1",
        )

    elif provider == "groq":
        return ChatOpenAI(
            api_key=SecretStr(api_key or os.getenv("GROQ_API_KEY", "")),
            model=model or "llama-3.1-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
        )

    elif provider == "openai-compatible":
        if not base_url:
            raise ValueError("base_url required for openai-compatible provider")
        return ChatOpenAI(
            api_key=SecretStr(api_key or ""),
            model=model or "gpt-4o",
            base_url=base_url,
        )

    else:
        raise ValueError(f"Unknown provider: {provider}")
