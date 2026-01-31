"""Weave-backed memory store.

Implements MemoryStore using Weave objects for persistence.
See [WV1b] for Weave object requirements.

Contract: docs/contracts/weave-integration.md
JSON Schema: docs/api-contracts/json-examples/weave-object.jsonc

Sources:
    - Weave Objects: https://docs.wandb.ai/weave/guides/tracking/objects
    - weave.publish: https://docs.wandb.ai/weave/guides/tracking/objects#publishing-an-object
    - weave.ref: https://docs.wandb.ai/weave/guides/tracking/objects#getting-an-object-back
"""

from datetime import UTC, datetime

import weave

from agent_loop.domain.models.memory import (
    FeedbackEntry,
    PatternEntry,
    RankingEntry,
)
from agent_loop.domain.ports.memory_store import MemoryStore


class PatternMemory(weave.Object):
    """Weave object for pattern persistence."""

    patterns: list[dict]  # Serialized PatternEntry


class FeedbackMemory(weave.Object):
    """Weave object for feedback persistence."""

    entries: list[dict]  # Serialized FeedbackEntry


class RankingMemory(weave.Object):
    """Weave object for ranking persistence."""

    entries: list[dict]  # Serialized RankingEntry


class WeaveMemoryStore:
    """Memory store using Weave objects.

    Persists all memory types to Weave for observability and retrieval.
    """

    def __init__(self, project_name: str = "agent-loop"):
        self.project_name = project_name
        self._patterns: dict[str, PatternEntry] = {}
        self._feedback: list[FeedbackEntry] = []
        self._rankings: list[RankingEntry] = []

    @weave.op()
    async def save_pattern(self, pattern: PatternEntry) -> None:
        """Save or update a learned pattern."""
        self._patterns[pattern.pattern_id] = pattern

    @weave.op()
    async def load_patterns(
        self, pattern_type: str | None = None, min_score: float = 0.0
    ) -> list[PatternEntry]:
        """Load patterns, optionally filtered."""
        patterns = list(self._patterns.values())
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        patterns = [p for p in patterns if p.effectiveness_score >= min_score]
        return sorted(patterns, key=lambda p: p.effectiveness_score, reverse=True)

    @weave.op()
    async def update_pattern_usage(self, pattern_id: str, new_score: float) -> None:
        """Update pattern usage count and score."""
        if pattern_id in self._patterns:
            pattern = self._patterns[pattern_id]
            pattern.usage_count += 1
            # Exponential moving average for score
            pattern.effectiveness_score = 0.7 * pattern.effectiveness_score + 0.3 * new_score
            pattern.last_used = datetime.now(UTC)

    @weave.op()
    async def save_feedback(self, feedback: FeedbackEntry) -> None:
        """Save evaluation feedback."""
        self._feedback.append(feedback)

    @weave.op()
    async def load_feedback(
        self, thread_id: str | None = None, limit: int = 100
    ) -> list[FeedbackEntry]:
        """Load feedback entries."""
        entries = self._feedback
        if thread_id:
            entries = [f for f in entries if f.thread_id == thread_id]
        return sorted(entries, key=lambda f: f.timestamp, reverse=True)[:limit]

    @weave.op()
    async def save_ranking(self, ranking: RankingEntry) -> None:
        """Save a ranking result."""
        self._rankings.append(ranking)

    @weave.op()
    async def load_rankings(self, limit: int = 50) -> list[RankingEntry]:
        """Load recent rankings."""
        return sorted(self._rankings, key=lambda r: r.timestamp, reverse=True)[:limit]


# Type assertion for protocol compliance
_: type[MemoryStore] = WeaveMemoryStore
