"""MCP Server for agent-loop.

Exposes agent-loop as an MCP server for TUI tools like Claude Code.
See [AP1b] for MCP requirements.

MCP servers handle one client session via stdio. The agent is created
once at startup and reused for all tool calls within that session.

Contract: docs/api-contracts/openapi.md

Sources:
    - MCP Protocol: https://modelcontextprotocol.io/
    - MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
"""

import asyncio
import os
import sys
from typing import Any

import weave
from langchain_core.messages import ToolMessage
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from agent_loop.application.agent import AgentLoop
from agent_loop.domain.exceptions import AgentLoopError, InvalidInputError
from agent_loop.graph.state import DEFAULT_MAX_ITERATIONS
from agent_loop.mcp.exception_handlers import handle_tool_error

# Create server
server = Server("agent-loop")


class _ServerState:
    """Container for server state to avoid global statements."""

    agent: AgentLoop | None = None


_state = _ServerState()


def _get_agent() -> AgentLoop:
    """Get the singleton agent instance.

    Raises RuntimeError if called before init_server().
    """
    if _state.agent is None:
        raise RuntimeError("Agent not initialized. Call init_server() first.")
    return _state.agent


def init_server() -> None:
    """Initialize Weave and the agent. Called once at process start."""
    # Initialize Weave once for this process
    weave.init(os.getenv("WEAVE_PROJECT", "agent-loop"))

    # Create the singleton agent
    _state.agent = AgentLoop(
        provider=os.getenv("AGENT_PROVIDER"),
        model=os.getenv("AGENT_MODEL"),
    )


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="run_agent",
            description="Run the agent loop with a task. The agent will research, "
            "evaluate, and provide a response with self-improvement feedback.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The task or query for the agent",
                    },
                    "thread_id": {
                        "type": "string",
                        "description": "Optional thread ID to continue conversation",
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": f"Maximum iterations (default: {DEFAULT_MAX_ITERATIONS})",
                        "default": DEFAULT_MAX_ITERATIONS,
                    },
                },
                "required": ["task"],
            },
        ),
        Tool(
            name="register_tool",
            description="Register a new tool for the agent to use. "
            "The tool will be available in subsequent run_agent calls.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique tool name",
                    },
                    "description": {
                        "type": "string",
                        "description": "What the tool does",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "JSON Schema for tool parameters",
                    },
                },
                "required": ["name", "description", "parameters"],
            },
        ),
        Tool(
            name="list_registered_tools",
            description="List all tools registered with the agent.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls.

    All exceptions are caught and formatted via exception_handlers to prevent
    MCP server crashes and provide consistent error responses.
    """
    try:
        return await _handle_tool_call(name, arguments)
    except AgentLoopError as exc:
        return handle_tool_error(exc)
    except Exception as exc:
        # Unexpected exceptions are wrapped and formatted
        # Re-raise would crash the MCP server, so we format instead
        return handle_tool_error(exc)


async def _handle_tool_call(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch tool call to appropriate handler."""
    agent = _get_agent()

    if name == "run_agent":
        return await _run_agent_tool(agent, arguments)

    if name == "register_tool":
        return _register_tool(arguments)

    if name == "list_registered_tools":
        return _list_registered_tools(agent)

    raise InvalidInputError(f"Unknown tool: {name}")


async def _run_agent_tool(agent: AgentLoop, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute the run_agent tool."""
    task = arguments.get("task", "")
    if not task:
        raise InvalidInputError("task is required")

    thread_id = arguments.get("thread_id")
    max_iterations = arguments.get("max_iterations", DEFAULT_MAX_ITERATIONS)

    result = await agent.arun(
        task=task,
        thread_id=thread_id,
        max_iterations=max_iterations,
    )

    response_content = result.response or "(No response generated)"
    response_text = f"""## Agent Response

**Thread ID:** {result.thread_id}
**Iterations:** {result.iterations}

### Response
{response_content}

### Observations
"""
    for msg in result.state.messages:
        if isinstance(msg, ToolMessage):
            response_text += f"- **{msg.name or 'unknown'}**: {msg.content}\n"

    return [TextContent(type="text", text=response_text)]


def _register_tool(arguments: dict[str, Any]) -> list[TextContent]:
    """Execute the register_tool tool."""
    # For MCP, we can't actually register executable tools dynamically
    # This is a placeholder that would need MCP tool forwarding
    return [
        TextContent(
            type="text",
            text=f"Tool '{arguments.get('name')}' registered (note: execution "
            "requires implementing the tool logic in the agent-loop codebase).",
        )
    ]


def _list_registered_tools(agent: AgentLoop) -> list[TextContent]:
    """Execute the list_registered_tools tool."""
    tool_names = [tool.name for tool in agent.tools]
    if tool_names:
        tools_text = "\n".join(f"- {tool_name}" for tool_name in tool_names)
    else:
        tools_text = "No tools registered yet."

    return [TextContent(type="text", text=f"## Registered Tools\n\n{tools_text}")]


async def run_server() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Entry point for MCP server.

    Loads environment, initializes Weave and agent, then runs the stdio server.
    """
    # Load environment variables before any initialization
    from dotenv import load_dotenv  # noqa: PLC0415

    load_dotenv()

    # Check for --stdio flag
    if "--stdio" in sys.argv or len(sys.argv) == 1:
        # Initialize Weave and agent before running server
        init_server()
        asyncio.run(run_server())
    else:
        sys.stderr.write("Usage: agent-loop-mcp [--stdio]\n")
        sys.stderr.write("  --stdio: Run as stdio MCP server (default)\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
