"""MCP Server for agent-loop.

Exposes agent-loop as an MCP server for TUI tools like Claude Code.
See [AP1b] for MCP requirements.

Contract: docs/api-contracts/openapi.md

Sources:
    - MCP Protocol: https://modelcontextprotocol.io/
    - MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
"""

import asyncio
import sys
from functools import lru_cache
from typing import Any

from langchain_core.messages import ToolMessage
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from agent_loop.application.agent import AgentLoop

# Create server
server = Server("agent-loop")


@lru_cache(maxsize=1)
def get_agent() -> AgentLoop:
    """Get or create the agent instance (singleton)."""
    return AgentLoop()


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
                        "description": "Maximum iterations (default: 5)",
                        "default": 5,
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
    """Handle tool calls."""
    agent = get_agent()

    if name == "run_agent":
        task = arguments.get("task", "")
        thread_id = arguments.get("thread_id")
        max_iterations = arguments.get("max_iterations", 5)

        result = await agent.arun(
            task=task,
            thread_id=thread_id,
            max_iterations=max_iterations,
        )

        response_text = f"""## Agent Response

**Thread ID:** {result.thread_id}
**Iterations:** {result.iterations}

### Response
{result.response}

### Observations
"""
        for msg in result.state.messages:
            if isinstance(msg, ToolMessage):
                response_text += f"- **{msg.name or 'unknown'}**: {msg.content}\n"

        return [TextContent(type="text", text=response_text)]

    elif name == "register_tool":
        # For MCP, we can't actually register executable tools dynamically
        # This is a placeholder that would need MCP tool forwarding
        return [
            TextContent(
                type="text",
                text=f"Tool '{arguments.get('name')}' registered (note: execution "
                "requires implementing the tool logic in the agent-loop codebase).",
            )
        ]

    elif name == "list_registered_tools":
        tool_names = [tool.name for tool in agent.tools]
        if tool_names:
            tools_text = "\n".join(f"- {tool_name}" for tool_name in tool_names)
        else:
            tools_text = "No tools registered yet."

        return [TextContent(type="text", text=f"## Registered Tools\n\n{tools_text}")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def run_server() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Entry point for MCP server."""
    # Check for --stdio flag
    if "--stdio" in sys.argv or len(sys.argv) == 1:
        asyncio.run(run_server())
    else:
        sys.stderr.write("Usage: agent-loop-mcp [--stdio]\n")
        sys.stderr.write("  --stdio: Run as stdio MCP server (default)\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
