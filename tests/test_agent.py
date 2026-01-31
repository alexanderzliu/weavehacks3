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
