"""MCP exception handlers.

Translates domain exceptions to MCP TextContent error responses.

Sources:
    - MCP Protocol: https://modelcontextprotocol.io/
"""

from mcp.types import TextContent

from agent_loop.domain.exceptions import AgentLoopError, ExecutionError


def format_error_response(exc: AgentLoopError) -> list[TextContent]:
    """Format domain exception as MCP TextContent error."""
    error_type = type(exc).__name__
    error_text = f"""## Error: {error_type}

**Message:** {exc.message}
"""
    if exc.cause:
        error_text += f"\n**Cause:** {type(exc.cause).__name__}: {exc.cause}"

    return [TextContent(type="text", text=error_text)]


def handle_tool_error(exc: Exception) -> list[TextContent]:
    """Handle any exception during tool execution.

    All domain exceptions inherit from AgentLoopError, so single check suffices.
    Unknown exceptions are wrapped in ExecutionError.
    """
    if isinstance(exc, AgentLoopError):
        return format_error_response(exc)

    # Unknown exception - wrap in ExecutionError
    wrapped = ExecutionError(str(exc), cause=exc)
    return format_error_response(wrapped)
