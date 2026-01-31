"""Memory Store port.

Defines the protocol for memory persistence.
Implementations use Weave objects. See [WV1b].

Contract: docs/contracts/weave-integration.md

Sources:
    - Weave Objects: https://docs.wandb.ai/weave/guides/tracking/objects
    - LangGraph Memory Store: https://langchain-ai.github.io/langgraph/concepts/persistence/#memory-store
"""

from typing import Protocol

from agent_loop.domain.models.memory import (
    FeedbackEntry,
    PatternEntry,
    RankingEntry,
)


class MemoryStore(Protocol):
    """Protocol for memory storage adapters.

    Implementations persist memory using Weave objects.
    """

    # Pattern memory
    async def save_pattern(self, pattern: PatternEntry) -> None:
        """Save or update a learned pattern."""
        ...

    async def load_patterns(
        self, pattern_type: str | None = None, min_score: float = 0.0
    ) -> list[PatternEntry]:
        """Load patterns, optionally filtered by type and minimum score."""
        ...

    async def update_pattern_usage(self, pattern_id: str, new_score: float) -> None:
        """Update pattern usage count and effectiveness score."""
        ...

    # Feedback memory
    async def save_feedback(self, feedback: FeedbackEntry) -> None:
        """Save evaluation feedback."""
        ...

    async def load_feedback(
        self, thread_id: str | None = None, limit: int = 100
    ) -> list[FeedbackEntry]:
        """Load feedback entries, optionally for a specific thread."""
        ...

    # Ranking memory
    async def save_ranking(self, ranking: RankingEntry) -> None:
        """Save a ranking result."""
        ...

    async def load_rankings(self, limit: int = 50) -> list[RankingEntry]:
        """Load recent rankings for learning."""
        ...
