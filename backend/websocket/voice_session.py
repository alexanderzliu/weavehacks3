"""Voice session management for human players.

This module manages voice sessions for human players, coordinating
between the WebSocket connection, Pipecat pipeline, and game runner.
"""

import asyncio
from typing import Optional, Dict, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import WebSocket


@dataclass
class VoiceSession:
    """A voice session for a human player."""
    session_id: str
    series_id: str
    player_id: str
    player_name: str
    websocket: Optional[WebSocket] = None
    room_url: Optional[str] = None
    room_token: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


class VoiceSessionManager:
    """Manages voice sessions for human players.

    Each series can have at most one human player with an active
    voice session. The manager handles:
    - Creating and destroying sessions
    - Routing WebSocket messages to the correct session
    - Coordinating with the HumanPlayerAdapter
    """

    def __init__(self):
        self._sessions: Dict[str, VoiceSession] = {}  # series_id -> session
        self._adapters: Dict[str, object] = {}  # series_id -> HumanPlayerAdapter
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        series_id: str,
        player_id: str,
        player_name: str,
        websocket: Optional[WebSocket] = None,
    ) -> VoiceSession:
        """Create a voice session for a human player.

        Args:
            series_id: The series the player is joining
            player_id: The player's unique ID
            player_name: The player's display name
            websocket: Optional WebSocket connection

        Returns:
            The created VoiceSession
        """
        from uuid import uuid4
        from voice_pipeline.pipeline import create_daily_room

        async with self._lock:
            # Check if session already exists
            if series_id in self._sessions:
                existing = self._sessions[series_id]
                if existing.is_active:
                    # Return existing session
                    return existing

            # Create Daily room for voice
            room_url, room_token = await create_daily_room()

            session = VoiceSession(
                session_id=str(uuid4()),
                series_id=series_id,
                player_id=player_id,
                player_name=player_name,
                websocket=websocket,
                room_url=room_url,
                room_token=room_token,
            )

            self._sessions[series_id] = session
            return session

    async def get_session(self, series_id: str) -> Optional[VoiceSession]:
        """Get the voice session for a series."""
        async with self._lock:
            return self._sessions.get(series_id)

    async def destroy_session(self, series_id: str) -> None:
        """Destroy the voice session for a series."""
        async with self._lock:
            if series_id in self._sessions:
                session = self._sessions[series_id]
                session.is_active = False
                del self._sessions[series_id]

            if series_id in self._adapters:
                del self._adapters[series_id]

    def set_adapter(self, series_id: str, adapter) -> None:
        """Associate a HumanPlayerAdapter with a series."""
        self._adapters[series_id] = adapter

    def get_adapter(self, series_id: str):
        """Get the HumanPlayerAdapter for a series."""
        return self._adapters.get(series_id)

    async def handle_human_input(
        self,
        series_id: str,
        input_type: str,
        data: dict,
    ) -> bool:
        """Handle input from the human player.

        Args:
            series_id: The series ID
            input_type: Type of input (speech, vote, night_action)
            data: Input data

        Returns:
            True if handled successfully
        """
        adapter = self.get_adapter(series_id)
        if not adapter:
            return False

        if input_type == "speech":
            adapter.receive_speech_text(data.get("text", ""))
            return True
        elif input_type == "vote":
            adapter.receive_vote(data.get("target", "no_lynch"))
            return True
        elif input_type == "night_action":
            adapter.receive_night_action(data.get("target", ""))
            return True

        return False


# Global voice session manager
voice_session_manager = VoiceSessionManager()
