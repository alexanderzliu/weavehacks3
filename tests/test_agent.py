"""Unit tests for AgentLoop."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from agent_loop.application.agent import AgentLoop


@pytest.fixture
def mock_dependencies(mocker):
    """Mock external dependencies."""
    mocker.patch("weave.init")
    mocker.patch("agent_loop.application.agent.create_llm_provider", return_value=MagicMock())
    mocker.patch("agent_loop.application.agent.WeaveMemoryStore", return_value=MagicMock())

    mock_compiled_graph = MagicMock()
    mock_graph = MagicMock()
    mock_graph.compile.return_value = mock_compiled_graph

    mocker.patch("agent_loop.application.agent.build_orchestrator_graph", return_value=mock_graph)

    return mock_compiled_graph


@pytest.mark.asyncio
async def test_agent_loop_run_success(mock_dependencies):
    """Test successful run of agent loop."""
    mock_compiled_graph = mock_dependencies

    # Mock graph output
    mock_compiled_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [HumanMessage(content="hello")],
            "task": "hello",
            "response": "Hi there",
            "iteration": 1,
            "max_iterations": 5,
            "evaluations": [],
            "rankings": [],
        }
    )

    agent = AgentLoop()
    result = await agent.arun("hello")

    assert result.response == "Hi there"
    assert result.iterations == 1
    mock_compiled_graph.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_thread_continuity_loads_checkpoint(mock_dependencies, mocker):
    """Test that thread continuity loads existing checkpoint state. [LG1d]"""
    mock_compiled_graph = mock_dependencies

    # Mock checkpointer.get to return existing checkpoint
    mock_checkpointer = MagicMock()
    mock_checkpointer.get.return_value = {"exists": True}  # Simulate existing checkpoint

    mocker.patch.object(AgentLoop, "__init__", lambda: None)
    mocker.patch.object(AgentLoop, "_compiled", mock_compiled_graph, create=True)
    mocker.patch.object(AgentLoop, "_checkpointer", mock_checkpointer, create=True)

    agent = AgentLoop.__new__(AgentLoop)

    # First call with thread_id
    mock_compiled_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="First message"),
                HumanMessage(content="First response"),
            ],
            "task": "First task",
            "response": "First response",
            "iteration": 1,
            "max_iterations": 5,
            "evaluations": [],
            "rankings": [],
        }
    )
    result1 = await agent.arun("First task", thread_id="thread-abc")
    assert result1.thread_id == "thread-abc"

    # Verify checkpointer.get was called to check for existing state
    mock_checkpointer.get.assert_called_with({"configurable": {"thread_id": "thread-abc"}})

    # Second call with same thread_id - should use get_state to check for checkpoint
    mock_compiled_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="First message"),
                HumanMessage(content="First response"),
                HumanMessage(content="Second message"),  # Appended
            ],
            "task": "Second task",
            "response": "Second response",
            "iteration": 2,
            "max_iterations": 5,
            "evaluations": [],
            "rankings": [],
        }
    )
    result2 = await agent.arun("Second task", thread_id="thread-abc")
    assert result2.thread_id == "thread-abc"

    # Verify that the second call passed a state with only the new message
    # (LangGraph's reducer appends to existing checkpoint messages)
    call_args = mock_compiled_graph.ainvoke.call_args
    passed_state = call_args[0][0]  # First positional arg
    assert len(passed_state.messages) == 1  # Only new message, reducer appends
    assert passed_state.messages[0].content == "Second task"
