"""Protocols for dependency injection - keeps game layer framework-free."""

from typing import Protocol

from models.schemas import GameEvent, PlayerSnapshotDict


class EventBroadcaster(Protocol):
    """Protocol for broadcasting game events to connected clients."""

    async def broadcast_event(self, series_id: str, event: GameEvent) -> None:
        """Broadcast a game event."""
        ...

    async def broadcast_series_status(
        self,
        series_id: str,
        status: str,
        game_number: int,
        total_games: int,
    ) -> None:
        """Broadcast series status update."""
        ...

    async def broadcast_snapshot(
        self,
        series_id: str,
        game_id: str,
        alive_player_ids: list[str],
        phase: str,
        day_number: int,
        players: list[PlayerSnapshotDict] | None = None,
    ) -> None:
        """Broadcast game state snapshot."""
        ...


class NullBroadcaster:
    """No-op broadcaster for testing or when no clients are connected."""

    async def broadcast_event(self, series_id: str, event: GameEvent) -> None:
        pass

    async def broadcast_series_status(
        self,
        series_id: str,
        status: str,
        game_number: int,
        total_games: int,
    ) -> None:
        pass

    async def broadcast_snapshot(
        self,
        series_id: str,
        game_id: str,
        alive_player_ids: list[str],
        phase: str,
        day_number: int,
        players: list[PlayerSnapshotDict] | None = None,
    ) -> None:
        pass
