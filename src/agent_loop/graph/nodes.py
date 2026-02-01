"""Graph node functions.

Each node is a step in the agent loop.
All nodes are traced via @weave.op(). See [WV1a].

Contract: docs/contracts/weave-integration.md, docs/contracts/langgraph-state.md

Sources:
    - Weave Ops: https://docs.wandb.ai/weave/guides/tracking/ops
    - LangGraph Nodes: https://docs.langchain.com/oss/python/langgraph/graph-api#nodes
"""

from collections.abc import Awaitable, Callable
from typing import TypedDict

import weave
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode as LangGraphToolNode

from agent_loop.domain.ports.memory_store import MemoryStore
from agent_loop.graph.prompts import AGENT_SYSTEM_PROMPT, EVALUATOR_PROMPT, RANKER_PROMPT
from agent_loop.graph.state import AgentState, Evaluation, Ranking


# [FS1b] Typed return dicts for each node
class AgentNodeResult(TypedDict, total=False):
    """Return type for agent node."""

    messages: list[AnyMessage]
    iteration: int


class EvaluatorNodeResult(TypedDict, total=False):
    """Return type for evaluator node."""

    evaluations: list[Evaluation]


class RankerNodeResult(TypedDict, total=False):
    """Return type for ranker node."""

    rankings: list[Ranking]


class DeciderNodeResult(TypedDict, total=False):
    """Return type for decider node."""

    response: str | None  # [FS1b] Optional when continuing iteration


NodeFunc = Callable[
    [AgentState],
    Awaitable[AgentNodeResult | EvaluatorNodeResult | RankerNodeResult | DeciderNodeResult],
]

# Configuration constants
MAX_RECENT_OBSERVATIONS = 5
MAX_RECENT_EVALUATIONS = 3
MIN_RESPONSE_LENGTH = 10  # Minimum characters for early termination

# Weave trace display names [WV1a]
TRACE_NAME_TOOLS = "Tools Node"
TRACE_NAME_AGENT = "Agent Node"
TRACE_NAME_EVALUATOR = "Evaluator Node"
TRACE_NAME_RANKER = "Ranker Node"
TRACE_NAME_DECIDER = "Decider Node"


def _extract_observations(messages: list[AnyMessage], limit: int = MAX_RECENT_OBSERVATIONS) -> str:
    """Extract recent tool observations from messages. [CC1a] Extracted helper."""
    observations = [
        f"- {m.name}: {m.content}" for m in messages[-limit:] if isinstance(m, ToolMessage)
    ]
    return "\n".join(observations) if observations else "No recent tool outputs."


def _extract_evaluations(evaluations: list[Evaluation], limit: int = MAX_RECENT_EVALUATIONS) -> str:
    """Extract recent evaluations as formatted text. [CC1a] Extracted helper."""
    recent = evaluations[-limit:]
    return "\n".join(f"Iteration {e.iteration}: {e.evaluation}" for e in recent)


def _is_complete_response(message: AnyMessage | None) -> bool:
    """Check if message is a complete agent response suitable for early termination.

    Returns True if the message is an AI response without tool calls
    and has substantial content (not just a short acknowledgment).
    """
    if message is None:
        return False

    if not isinstance(message, AIMessage):
        return False

    # Has tool calls - agent wants to use tools, don't terminate early
    if message.tool_calls:
        return False

    # Check content length - avoid terminating on empty or trivial responses
    content = str(message.content) if message.content else ""
    return len(content) >= MIN_RESPONSE_LENGTH


def create_nodes(
    llm: BaseChatModel,
    _memory: MemoryStore,  # Reserved for future pattern/ranking operations
    tools: list[BaseTool],
) -> dict[str, NodeFunc]:
    """Create node functions with dependencies injected."""

    # [WV1a] Wrap LangGraph's ToolNode for Weave tracing
    # Source: https://langchain-ai.github.io/langgraph/reference/prebuilt/#toolnode
    _tools_node = LangGraphToolNode(tools)

    @weave.op(call_display_name=TRACE_NAME_TOOLS)
    async def tools_node(state: AgentState) -> AgentNodeResult:
        """Execute tool calls with Weave tracing. [WV1a] Wrapper for ToolNode."""
        result: dict[str, list[AnyMessage]] = await _tools_node.ainvoke(state)
        messages: list[AnyMessage] = result.get("messages", [])
        return AgentNodeResult(messages=messages)

    @weave.op(call_display_name=TRACE_NAME_AGENT)
    async def agent_node(state: AgentState) -> AgentNodeResult:
        """Main agent reasoning node.

        Uses binding to attach tools to the LLM.
        """
        # Add system prompt
        system_msg = SystemMessage(content=AGENT_SYSTEM_PROMPT.format(task=state.task))
        messages = [system_msg] + state.messages

        # Bind tools to LLM
        # Source: https://python.langchain.com/docs/how_to/tool_calling/
        llm_with_tools = llm.bind_tools(tools)

        # Call LLM
        response = await llm_with_tools.ainvoke(messages)

        # Return typed dict updates for reducer [FS1b]
        return AgentNodeResult(
            messages=[response],
            iteration=state.iteration + 1,
        )

    @weave.op(call_display_name=TRACE_NAME_EVALUATOR)
    async def evaluator_node(state: AgentState) -> EvaluatorNodeResult:
        """Evaluate the current state and observations.

        Analyzes agent response and recent tool outputs to assess progress.
        """
        # [CC1a] Use extracted helper for observation formatting
        obs_text = _extract_observations(state.messages)

        # Extract agent response content (last AIMessage without tool calls)
        last_message = state.messages[-1] if state.messages else None
        if isinstance(last_message, AIMessage):
            response_text = (
                str(last_message.content) if last_message.content else "No direct response"
            )
        else:
            response_text = "No agent response yet"

        eval_prompt = EVALUATOR_PROMPT.format(
            task=state.task,
            response=response_text,
            observations=obs_text,
        )
        messages = [HumanMessage(content=eval_prompt)]

        response = await llm.ainvoke(messages)

        # Store evaluation [FS1b]
        return EvaluatorNodeResult(
            evaluations=[
                Evaluation(
                    iteration=state.iteration,
                    evaluation=str(response.content),
                )
            ]
        )

    @weave.op(call_display_name=TRACE_NAME_RANKER)
    async def ranker_node(state: AgentState) -> RankerNodeResult:
        """Rank responses and provide feedback.

        Compares current iteration against previous ones.
        """
        # [CC1a] Use extracted helper for evaluation formatting
        eval_text = _extract_evaluations(state.evaluations)

        # Extract agent response content (last AIMessage without tool calls)
        last_message = state.messages[-1] if state.messages else None
        if isinstance(last_message, AIMessage):
            response_text = (
                str(last_message.content) if last_message.content else "No direct response"
            )
        else:
            response_text = "No agent response yet"

        rank_prompt = RANKER_PROMPT.format(
            task=state.task,
            response=response_text,
            evaluations=eval_text,
        )
        messages = [HumanMessage(content=rank_prompt)]

        response = await llm.ainvoke(messages)

        # [FS1b] Return typed dict
        return RankerNodeResult(
            rankings=[
                Ranking(
                    iteration=state.iteration,
                    ranking=str(response.content),
                )
            ]
        )

    @weave.op(call_display_name=TRACE_NAME_DECIDER)
    async def decider_node(state: AgentState) -> DeciderNodeResult:
        """Decide whether to continue or respond.

        Early termination: if the agent provided a direct response (no tool calls)
        with substantial content, use it immediately instead of looping.
        """
        # Check for early termination: agent gave direct response without tools
        last_message = state.messages[-1] if state.messages else None
        if last_message is not None and _is_complete_response(last_message):
            return DeciderNodeResult(response=str(last_message.content))

        # Check max iterations - generate final response if at limit
        if state.iteration >= state.max_iterations:
            messages = state.messages + [
                HumanMessage(content="Please provide your final response to the task.")
            ]
            response = await llm.ainvoke(messages)
            return DeciderNodeResult(response=str(response.content))

        return DeciderNodeResult()

    return {
        "agent": agent_node,
        "tools": tools_node,
        "evaluator": evaluator_node,
        "ranker": ranker_node,
        "decider": decider_node,
    }
