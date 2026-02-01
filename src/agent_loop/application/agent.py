"""Main AgentLoop use case.

The primary entry point for running the agent loop.
Coordinates domain logic, adapters, and LangGraph orchestration.

See [AR1d] Application layer orchestrates domain + adapters.
See docs/contracts/project-code-requirements.md for full requirements.

Sources:
    - Weave Init: https://docs.wandb.ai/weave/quickstart
    - LangGraph Compile: https://docs.langchain.com/oss/python/langgraph/graph-api#compiling-your-graph
    - LangGraph Checkpointer: https://langchain-ai.github.io/langgraph/concepts/persistence/
"""

import asyncio
import uuid
from typing import TYPE_CHECKING

import weave

if TYPE_CHECKING:
    from weave.trace.weave_client import Call

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool

from agent_loop.adapters.llm.factory import create_llm_provider
from agent_loop.adapters.memory.weave_memory import WeaveMemoryStore
from agent_loop.domain.ports.memory_store import MemoryStore
from agent_loop.graph.orchestrator import build_orchestrator_graph
from agent_loop.graph.state import DEFAULT_MAX_ITERATIONS, AgentState

# Display name truncation limit for Weave traces
_TASK_DISPLAY_LIMIT = 50


def _format_agent_loop_display_name(call: "Call") -> str:
    """Format display name for agent loop traces.

    Extracts task from call inputs and truncates for readability.
    See [WV1c] - traces are primary observability layer.
    """
    task = call.inputs.get("task", "unknown")
    truncated = task[:_TASK_DISPLAY_LIMIT] if len(task) > _TASK_DISPLAY_LIMIT else task
    return f"Agent Loop: {truncated}"


class AgentLoopResult:
    """Result from running the agent loop."""

    def __init__(
        self,
        thread_id: str,
        response: str | None,
        iterations: int,
        state: AgentState,
    ):
        self.thread_id = thread_id
        self.response = response
        self.iterations = iterations
        self.state = state

    @property
    def has_response(self) -> bool:
        """Check if a response was generated."""
        return self.response is not None


class AgentLoop:
    """Main agent loop orchestrator.

    Provides a simple interface for running the self-improving agent loop.
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        tools: list[BaseTool] | None = None,
    ):
        """Initialize the agent loop.

        Requires weave.init() to be called before instantiation.
        For FastAPI, this happens in lifespan. For MCP, in main().

        Args:
            provider: LLM provider (openai, ollama, together, groq, openai-compatible).
                      If None, auto-detects based on environment variables.
            model: Model name
            api_key: API key for provider
            base_url: Base URL for OpenAI-compatible endpoints
            tools: List of LangChain tools to enable
        """
        # Create adapters
        self.llm: BaseChatModel = create_llm_provider(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        self.memory: MemoryStore = WeaveMemoryStore()
        self.tools: list[BaseTool] = tools or []

        # Build the graph
        self._graph = build_orchestrator_graph(self.llm, self.memory, self.tools)
        self._compiled = self._graph.compile()

    def add_tool(self, tool_instance: BaseTool) -> "AgentLoop":
        """Add a tool to the agent."""
        self.tools.append(tool_instance)
        # Rebuild graph to include new tool
        self._graph = build_orchestrator_graph(self.llm, self.memory, self.tools)
        self._compiled = self._graph.compile()
        return self

    @weave.op(call_display_name=_format_agent_loop_display_name)
    async def arun(
        self,
        task: str,
        thread_id: str | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> AgentLoopResult:
        """Run the agent loop asynchronously.

        Args:
            task: The task or query for the agent
            thread_id: Thread ID for conversation continuity
            max_iterations: Maximum iterations before stopping

        Returns:
            AgentLoopResult with response and metadata
        """
        thread_id = thread_id or str(uuid.uuid4())

        # Create initial state (history persistence requires LangGraph Checkpointer)
        initial_state = AgentState(
            messages=[HumanMessage(content=task)],
            task=task,
            max_iterations=max_iterations,
        )

        # Run the graph
        config = {"configurable": {"thread_id": thread_id}}
        final_state_dict = await self._compiled.ainvoke(initial_state, config=config)  # type: ignore[arg-type]

        # Parse result
        result_state = AgentState(**final_state_dict)

        return AgentLoopResult(
            thread_id=thread_id,
            response=result_state.response,
            iterations=result_state.iteration,
            state=result_state,
        )

    def run(
        self,
        task: str,
        thread_id: str | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> AgentLoopResult:
        """Run the agent loop synchronously.

        Convenience wrapper around arun for sync contexts.
        """
        return asyncio.run(self.arun(task, thread_id, max_iterations))
