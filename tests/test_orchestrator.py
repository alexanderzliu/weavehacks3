"""Tests for orchestrator graph routing logic.

Tests critical routing behavior to ensure consistent response quality validation
between iteration limit handling and normal flow decision making.
"""

import pytest
from langchain_core.messages import AIMessage

from agent_loop.graph.nodes import _is_complete_response
from agent_loop.graph.orchestrator import route_after_agent
from agent_loop.graph.state import AgentState


class TestRouteAfterAgent:
    """Test route_after_agent function for consistent validation behavior."""

    @pytest.fixture
    def base_state(self):
        """Base state factory for testing."""
        return AgentState(task="test task", messages=[], iteration=5, max_iterations=10)

    def test_short_response_at_iteration_limit_goes_to_evaluator(self, base_state):
        """Short responses (< MIN_RESPONSE_LENGTH) at iteration limit should go to evaluator.

        This ensures consistent behavior with decider_node which uses _is_complete_response
        to validate response quality before allowing early termination.
        """
        short_response = AIMessage(content="Hi")  # 2 characters < MIN_RESPONSE_LENGTH (10)
        state = base_state.model_copy(
            update={
                "messages": [short_response],
                "iteration": 10,
                "max_iterations": 10,  # At limit
            }
        )

        result = route_after_agent(state)
        assert result == "evaluator", (
            f"Short response at limit should go to evaluator, got '{result}'"
        )

    def test_adequate_response_at_iteration_limit_can_end(self, base_state):
        """Adequate responses (>= MIN_RESPONSE_LENGTH) at iteration limit can end immediately."""
        adequate_response = AIMessage(content="This is a complete response")  # 27 chars >= 10
        state = base_state.model_copy(
            update={
                "messages": [adequate_response],
                "iteration": 10,
                "max_iterations": 10,  # At limit
            }
        )

        result = route_after_agent(state)
        assert result == "__end__", f"Adequate response at limit should end, got '{result}'"

    def test_tool_calls_at_iteration_limit_skip_tools(self, base_state):
        """Tool calls at iteration limit should skip tools and go to evaluator."""
        response_with_tools = AIMessage(
            content="I'll use a tool",
            tool_calls=[{"name": "test_tool", "args": {}, "id": "call_1"}],
        )
        state = base_state.model_copy(
            update={
                "messages": [response_with_tools],
                "iteration": 10,
                "max_iterations": 10,  # At limit
            }
        )

        result = route_after_agent(state)
        assert result == "evaluator", f"Tool calls at limit should go to evaluator, got '{result}'"

    def test_normal_flow_with_tools_routes_to_tools(self, base_state):
        """Normal flow with tool calls should route to tools."""
        response_with_tools = AIMessage(
            content="I'll use a tool",
            tool_calls=[{"name": "test_tool", "args": {}, "id": "call_1"}],
        )
        state = base_state.model_copy(
            update={
                "messages": [response_with_tools],
                "iteration": 5,
                "max_iterations": 10,  # Not at limit
            }
        )

        result = route_after_agent(state)
        assert result == "tools", f"Normal flow with tools should go to tools, got '{result}'"

    def test_normal_flow_without_tools_routes_to_evaluator(self, base_state):
        """Normal flow without tool calls should route to evaluator."""
        response = AIMessage(content="This is a response")
        state = base_state.model_copy(
            update={
                "messages": [response],
                "iteration": 5,
                "max_iterations": 10,  # Not at limit
            }
        )

        result = route_after_agent(state)
        assert result == "evaluator", (
            f"Normal flow without tools should go to evaluator, got '{result}'"
        )

    def test_consistency_with_decider_node_validation(self):
        """Verify route_after_agent uses same validation as decider_node.

        This is the core regression test for the reported issue.
        """
        # Test cases that should NOT pass validation
        short_responses = [
            AIMessage(content=""),  # Empty
            AIMessage(content="Hi"),  # 2 chars
            AIMessage(content="1234567"),  # 7 chars
        ]

        # Test cases that SHOULD pass validation
        adequate_responses = [
            AIMessage(content="1234567890"),  # Exactly 10 chars
            AIMessage(content="This is adequate"),  # 17 chars
            AIMessage(content="A" * 50),  # 50 chars
        ]

        # Verify _is_complete_response behavior
        for response in short_responses:
            assert not _is_complete_response(response), (
                f"Short response '{response.content}' should not be complete"
            )

        for response in adequate_responses:
            assert _is_complete_response(response), (
                f"Adequate response '{response.content}' should be complete"
            )

        # Verify route_after_agent applies same logic at iteration limit
        for response in short_responses:
            state = AgentState(
                task="test",
                messages=[response],
                iteration=10,
                max_iterations=10,
            )
            result = route_after_agent(state)
            assert result == "evaluator", (
                f"Short response at limit should go to evaluator, got '{result}'"
            )

        for response in adequate_responses:
            state = AgentState(
                task="test",
                messages=[response],
                iteration=10,
                max_iterations=10,
            )
            result = route_after_agent(state)
            assert result == "__end__", f"Adequate response at limit should end, got '{result}'"
