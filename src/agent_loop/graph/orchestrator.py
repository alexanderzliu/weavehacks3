"""Orchestrator graph for the agent loop.

Uses LangGraph StateGraph for orchestration. See [LG1a].

Contract: docs/contracts/langgraph-state.md
JSON Schema: docs/api-contracts/json-examples/agentloop-state.jsonc

Sources:
    - LangGraph StateGraph: https://docs.langchain.com/oss/python/langgraph/graph-api#stategraph
    - LangGraph Edges: https://docs.langchain.com/oss/python/langgraph/graph-api#edges
    - LangGraph Nodes: https://docs.langchain.com/oss/python/langgraph/graph-api#nodes
"""

from typing import Any, Literal, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from agent_loop.domain.ports.memory_store import MemoryStore
from agent_loop.graph.nodes import create_nodes
from agent_loop.graph.state import AgentState


def route_after_agent(state: AgentState) -> Literal["tools", "evaluator", "__end__"]:
    """Route after agent node based on decision.

    Checks iteration limit BEFORE routing to tools to prevent exceeding max_iterations.
    If at limit, tool calls are skipped and we proceed to evaluator for final response.
    """
    # Check iteration limit first - if at limit, skip tools even if requested
    # This prevents the agent from running more times than max_iterations
    if state.is_iteration_limit_reached:
        return "evaluator"

    last_message = state.messages[-1]

    # If agent made tool calls, go to tools
    # Source: https://python.langchain.com/docs/how_to/tool_calling/#checking-for-tool-calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    # If agent just responded, go to evaluator
    return "evaluator"


def route_after_evaluator(_state: AgentState) -> Literal["ranker"]:
    """Route after evaluator node."""
    return "ranker"


def route_after_decider(state: AgentState) -> Literal["agent", "__end__"]:
    """Route after decider node."""
    if state.response:
        return cast(Literal["__end__"], END)

    if state.is_iteration_limit_reached:
        return cast(Literal["__end__"], END)

    return "agent"


def build_orchestrator_graph(
    llm: BaseChatModel,
    memory: MemoryStore,
    tools: list[BaseTool],
) -> StateGraph:
    """Build the main orchestrator graph.

    Architecture:
    ```
    ┌─────────┐    ┌─────────┐
    │  Agent  │───▶│  Tools  │
    └─────────┘    └─────────┘
         ▲              │
         │              │
         └──────────────┘
         │
         ▼
    ┌───────────┐
    │ Evaluator │
    └───────────┘
         │
    ┌─────────┐
    │ Ranker  │
    └─────────┘
         │
    ┌─────────┐
    │ Decider │ ──▶ Response / Next Iteration
    └─────────┘
    ```
    """
    # Create node functions with dependencies injected
    nodes = create_nodes(llm, memory, tools)

    # Build graph
    graph = StateGraph(AgentState)

    # Add nodes
    # Casting nodes to Any to bypass strict type checking on NodeFunc vs StateNode mismatch
    # LangGraph is flexible, but ty stubs are strict about RunnableConfig presence
    graph.add_node("agent", cast(Any, nodes["agent"]))
    graph.add_node("tools", cast(Any, nodes["tools"]))
    graph.add_node("evaluator", cast(Any, nodes["evaluator"]))
    graph.add_node("ranker", cast(Any, nodes["ranker"]))
    graph.add_node("decider", cast(Any, nodes["decider"]))

    # Set entry point
    graph.set_entry_point("agent")

    # Add edges
    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tools": "tools",
            "evaluator": "evaluator",
            END: END,
        },
    )

    # Tools loop back to agent to process result
    graph.add_edge("tools", "agent")

    graph.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {"ranker": "ranker"},
    )

    graph.add_edge("ranker", "decider")

    graph.add_conditional_edges(
        "decider",
        route_after_decider,
        {
            "agent": "agent",
            END: END,
        },
    )

    return graph
