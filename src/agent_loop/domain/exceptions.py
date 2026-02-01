"""Domain exceptions for agent-loop.

Framework-free exception hierarchy per [CC1d] and [AR1b].
All exceptions are typed per [RC1c].

These exceptions are translated to HTTP/MCP responses at boundaries.
"""


class AgentLoopError(Exception):
    """Base exception for all agent-loop domain errors."""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause


class InvalidInputError(AgentLoopError):
    """Invalid input provided to agent operation.

    Translates to HTTP 400 / MCP error.
    """


class ProviderError(AgentLoopError):
    """LLM provider failed or misconfigured.

    Translates to HTTP 502 / MCP error.
    """


class AuthenticationError(AgentLoopError):
    """Authentication with LLM provider failed.

    Translates to HTTP 401 / MCP error.
    """


class ExecutionError(AgentLoopError):
    """Agent execution failed during processing.

    Translates to HTTP 500 / MCP error.
    """


class ConfigurationError(AgentLoopError):
    """Required configuration is missing or invalid.

    Provides human-readable guidance on how to fix the configuration.
    Translates to HTTP 500 / MCP error (startup failure).
    """

    def __init__(
        self,
        message: str,
        *,
        env_var: str | None = None,
        help_url: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.env_var = env_var
        self.help_url = help_url
