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

from agent_loop.domain.exceptions import ConfigurationError


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for an LLM provider."""

    default_model: str
    api_key_env: str
    display_name: str  # Human-readable provider name for error messages
    base_url: str | None = None
    api_key_placeholder: str | None = None  # For providers that don't need real keys
    detection_env: str | None = None  # Env var to check for auto-detection
    detection_priority: int = 100  # Lower = higher priority for auto-detection
    # Env vars for lazy resolution (read at call time, not import time)
    base_url_env: str | None = None  # Env var for base_url
    default_model_env: str | None = None  # Env var for default_model
    # Help URL for API key documentation
    api_key_help_url: str | None = None


# [CC1b] Registry pattern replaces type switch (>3 cases)
# NOTE: Env vars are resolved lazily via _resolve_config() to avoid import-time issues
_PROVIDER_REGISTRY: dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        default_model="gpt-5-mini",
        api_key_env="OPENAI_API_KEY",
        display_name="OpenAI",
        detection_env="OPENAI_API_KEY",
        detection_priority=20,
        api_key_help_url="https://platform.openai.com/api-keys",
    ),
    "ollama": ProviderConfig(
        default_model="llama3.2",
        api_key_env="OLLAMA_API_KEY",
        display_name="Ollama",
        base_url="http://localhost:11434/v1",  # Default, overridden by env
        base_url_env="OLLAMA_HOST",  # Lazy resolution
        api_key_placeholder="ollama",
        detection_env="OLLAMA_HOST",
        detection_priority=50,
        api_key_help_url="https://ollama.ai/download",
    ),
    "together": ProviderConfig(
        default_model="meta-llama/Llama-3-70b-chat-hf",
        api_key_env="TOGETHER_API_KEY",
        display_name="Together AI",
        base_url="https://api.together.xyz/v1",
        detection_env="TOGETHER_API_KEY",
        detection_priority=40,
        api_key_help_url="https://api.together.xyz/settings/api-keys",
    ),
    "groq": ProviderConfig(
        default_model="llama-3.1-70b-versatile",
        api_key_env="GROQ_API_KEY",
        display_name="Groq",
        base_url="https://api.groq.com/openai/v1",
        detection_env="GROQ_API_KEY",
        detection_priority=30,
        api_key_help_url="https://console.groq.com/keys",
    ),
    "openai-compatible": ProviderConfig(
        default_model="gpt-5-mini",  # Default, overridden by env
        default_model_env="OPENAI_COMPATIBLE_MODEL",  # Lazy resolution
        api_key_env="OPENAI_COMPATIBLE_API_KEY",
        display_name="OpenAI-Compatible Endpoint",
        base_url_env="OPENAI_COMPATIBLE_BASE_URL",  # Lazy resolution (required)
        detection_env="OPENAI_COMPATIBLE_BASE_URL",
        detection_priority=10,  # Highest priority (explicit custom endpoint)
    ),
}


def _resolve_config(config: ProviderConfig) -> tuple[str, str | None]:
    """Resolve config values that may come from environment variables.

    Called at runtime (not import time) to ensure dotenv has been loaded.

    Returns:
        Tuple of (resolved_model, resolved_base_url)
    """
    # Resolve default_model: env var overrides static default
    resolved_model = config.default_model
    if config.default_model_env:
        resolved_model = os.getenv(config.default_model_env, config.default_model)

    # Resolve base_url: env var overrides static value
    resolved_base_url = config.base_url
    if config.base_url_env:
        env_value = os.getenv(config.base_url_env)
        if env_value:
            # OLLAMA_HOST needs /v1 suffix appended
            if config.base_url_env == "OLLAMA_HOST":
                resolved_base_url = env_value + "/v1"
            else:
                resolved_base_url = env_value

    return resolved_model, resolved_base_url


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
        ValueError: If provider is unknown
        ConfigurationError: If required configuration is missing (API key, base_url)
    """
    # Auto-detect provider if not specified
    resolved_provider = provider or _detect_default_provider()

    # Lookup in registry
    config = _PROVIDER_REGISTRY.get(resolved_provider)
    if not config:
        raise ValueError(f"Unknown provider: {resolved_provider}")

    # Resolve env vars at runtime (not import time)
    config_model, config_base_url = _resolve_config(config)

    # Use explicit params if provided, otherwise use resolved config
    resolved_base_url = base_url or config_base_url
    if resolved_provider == "openai-compatible" and not resolved_base_url:
        raise ConfigurationError(
            f"The {config.display_name} requires a base URL.\n\n"
            "To fix this, set the OPENAI_COMPATIBLE_BASE_URL environment variable:\n"
            "  export OPENAI_COMPATIBLE_BASE_URL=https://your-api-endpoint.com/v1",
            env_var="OPENAI_COMPATIBLE_BASE_URL",
        )

    # Resolve API key (placeholder allows providers like Ollama to skip real keys)
    resolved_key = api_key or config.api_key_placeholder or os.getenv(config.api_key_env, "")

    # Validate API key is present (unless provider uses placeholder)
    if not resolved_key:
        help_text = _build_missing_api_key_message(config, resolved_provider)
        raise ConfigurationError(
            help_text,
            env_var=config.api_key_env,
            help_url=config.api_key_help_url,
        )

    return ChatOpenAI(
        api_key=SecretStr(resolved_key),  # type: ignore[call-arg]
        model=model or config_model,  # type: ignore[call-arg]
        base_url=resolved_base_url,  # type: ignore[call-arg]
    )


def _build_missing_api_key_message(config: ProviderConfig, provider_name: str) -> str:
    """Build a helpful error message for a missing API key."""
    lines = [
        f"No API key found for {config.display_name}.",
        "",
        f"To fix this, set the {config.api_key_env} environment variable:",
        f"  export {config.api_key_env}=your-api-key-here",
    ]

    if config.api_key_help_url:
        lines.extend(["", f"Get your API key at: {config.api_key_help_url}"])

    # Add provider-specific tips
    if provider_name == "openai":
        lines.extend(
            [
                "",
                "Tip: You can also use a different provider by setting AGENT_PROVIDER:",
                "  export AGENT_PROVIDER=groq      # Fast inference with Groq",
                "  export AGENT_PROVIDER=together  # Together AI",
                "  export AGENT_PROVIDER=ollama    # Local models with Ollama",
            ]
        )

    return "\n".join(lines)
