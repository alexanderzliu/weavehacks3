"""WebSocket connection manager for live game streaming."""

import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from db import crud
from db.database import get_db_session
from models.schemas import GameEvent, PlayerSnapshotDict, Visibility

logger = logging.getLogger(__name__)

# Exceptions that indicate a closed/broken WebSocket connection
WebSocketSendError = (WebSocketDisconnect, RuntimeError, ConnectionError)

router = APIRouter()


class WSMessage(BaseModel):
    type: str
    payload: dict


class Subscription:
    def __init__(
        self,
        websocket: WebSocket,
        series_id: str,
        viewer_mode: bool = True,
        player_id: str | None = None,
        player_role: str | None = None,
        audio_enabled: bool = False,
    ):
        self.id = str(uuid4())
        self.websocket = websocket
        self.series_id = series_id
        self.viewer_mode = viewer_mode
        self.player_id = player_id
        self.player_role = player_role
        self.audio_enabled = audio_enabled


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self._subscriptions: dict[str, list[Subscription]] = {}  # series_id -> subscriptions
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a WebSocket connection."""
        await websocket.accept()

    async def disconnect(self, subscription: Subscription) -> None:
        """Remove a subscription."""
        async with self._lock:
            if subscription.series_id in self._subscriptions:
                self._subscriptions[subscription.series_id] = [
                    s
                    for s in self._subscriptions[subscription.series_id]
                    if s.id != subscription.id
                ]
                if not self._subscriptions[subscription.series_id]:
                    del self._subscriptions[subscription.series_id]

    async def subscribe(
        self,
        websocket: WebSocket,
        series_id: str,
        viewer_mode: bool = True,
        player_id: str | None = None,
        player_role: str | None = None,
        audio_enabled: bool = False,
    ) -> Subscription:
        """Subscribe a WebSocket to a series."""
        subscription = Subscription(
            websocket=websocket,
            series_id=series_id,
            viewer_mode=viewer_mode,
            player_id=player_id,
            player_role=player_role,
            audio_enabled=audio_enabled,
        )
        async with self._lock:
            if series_id not in self._subscriptions:
                self._subscriptions[series_id] = []
            self._subscriptions[series_id].append(subscription)
        return subscription

    async def set_audio_enabled(self, subscription_id: str, enabled: bool) -> None:
        """Update audio preference for a subscription."""
        async with self._lock:
            for series_id, subs in self._subscriptions.items():
                for sub in subs:
                    if sub.id == subscription_id:
                        sub.audio_enabled = enabled
                        logger.info(
                            "Audio %s for subscription %s (series %s)",
                            "enabled" if enabled else "disabled",
                            subscription_id,
                            series_id,
                        )
                        return

    def has_audio_listeners(self, series_id: str) -> bool:
        """Check if any subscriber wants audio for this series."""
        subs = self._subscriptions.get(series_id, [])
        has_listeners = any(sub.audio_enabled for sub in subs)
        logger.info(
            "Audio listeners check for series %s: %s (%d subs, audio states: %s)",
            series_id,
            has_listeners,
            len(subs),
            [sub.audio_enabled for sub in subs],
        )
        return has_listeners

    def _should_send_event(self, subscription: Subscription, event: GameEvent) -> bool:
        """Determine if an event should be sent to a subscription."""
        visibility = event.visibility

        # Viewers see everything
        if subscription.viewer_mode:
            return True

        # Public events go to everyone
        if visibility == Visibility.PUBLIC:
            return True

        # Mafia events go to mafia players
        if visibility == Visibility.MAFIA and subscription.player_role == "mafia":
            return True

        # Private events go only to the actor
        if visibility == Visibility.PRIVATE and subscription.player_id == event.actor_id:
            return True

        # Viewer-only events are for viewers (handled above)
        return False

    async def broadcast_event(self, series_id: str, event: GameEvent) -> None:
        """Broadcast a game event to all relevant subscribers."""
        async with self._lock:
            subscriptions = self._subscriptions.get(series_id, []).copy()

        for sub in subscriptions:
            if self._should_send_event(sub, event):
                try:
                    await self._send_message(
                        sub.websocket,
                        WSMessage(
                            type="event",
                            payload=event.model_dump(mode="json"),
                        ),
                    )
                except WebSocketSendError:
                    # Connection closed - will be cleaned up on next disconnect
                    logger.debug("WebSocket send failed for subscription %s", sub.id)

    async def broadcast_series_status(
        self,
        series_id: str,
        status: str,
        game_number: int,
        total_games: int,
    ) -> None:
        """Broadcast series status update."""
        async with self._lock:
            subscriptions = self._subscriptions.get(series_id, []).copy()

        message = WSMessage(
            type="series_status",
            payload={
                "series_id": series_id,
                "status": status,
                "game_number": game_number,
                "total_games": total_games,
            },
        )
        for sub in subscriptions:
            try:
                await self._send_message(sub.websocket, message)
            except WebSocketSendError:
                logger.debug("WebSocket send failed for subscription %s", sub.id)

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
        async with self._lock:
            subscriptions = self._subscriptions.get(series_id, []).copy()

        message = WSMessage(
            type="snapshot",
            payload={
                "game_id": game_id,
                "alive_player_ids": alive_player_ids,
                "phase": phase,
                "day_number": day_number,
                "players": players or [],
            },
        )
        for sub in subscriptions:
            try:
                await self._send_message(sub.websocket, message)
            except WebSocketSendError:
                logger.debug("WebSocket send failed for subscription %s", sub.id)

    async def send_error(
        self, websocket: WebSocket, message: str, details: dict | None = None
    ) -> None:
        """Send an error message to a specific WebSocket."""
        await self._send_message(
            websocket,
            WSMessage(
                type="error",
                payload={"message": message, "details": details or {}},
            ),
        )

    async def _send_message(self, websocket: WebSocket, message: WSMessage) -> None:
        """Send a message to a WebSocket."""
        await websocket.send_json(message.model_dump())

    async def send_initial_snapshot(self, websocket: WebSocket, series_id: str) -> None:
        """Send the current game state snapshot to a newly subscribed client."""
        try:
            async with get_db_session() as db:
                game = await crud.get_active_game_for_series(db, series_id)
                if not game:
                    return

                # Build player list with roles
                players = [
                    {
                        "name": gp.player.name,
                        "role": gp.role,
                        "is_alive": gp.is_alive,
                    }
                    for gp in game.game_players
                ]

                alive_player_names = [p["name"] for p in players if p["is_alive"]]

                message = WSMessage(
                    type="snapshot",
                    payload={
                        "game_id": game.id,
                        "alive_player_ids": alive_player_names,
                        "phase": game.status,
                        "day_number": game.day_number,
                        "players": players,
                    },
                )
                await self._send_message(websocket, message)
        except Exception as e:
            # Don't fail subscription if initial snapshot fails
            logger.warning("Failed to send initial snapshot for series %s: %s", series_id, e)

    async def send_to_player(
        self,
        series_id: str,
        player_id: str,
        msg_type: str,
        payload: dict,
    ) -> bool:
        """Send a message to a specific player in a series.

        Args:
            series_id: The series ID
            player_id: The target player ID
            msg_type: Message type
            payload: Message payload

        Returns:
            True if message was sent successfully
        """
        async with self._lock:
            subscriptions = self._subscriptions.get(series_id, []).copy()

        message = WSMessage(type=msg_type, payload=payload)
        for sub in subscriptions:
            if sub.player_id == player_id:
                try:
                    await self._send_message(sub.websocket, message)
                    return True
                except Exception as e:
                    logger.debug("Failed to send to player %s: %s", player_id, e)
        return False


# Global connection manager instance
ws_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):  # noqa: C901, PLR0912
    """WebSocket endpoint for live game streaming."""
    await ws_manager.connect(websocket)
    subscription: Subscription | None = None

    try:
        while True:
            raw_message = await websocket.receive_json()

            msg_type = raw_message.get("type")
            payload = raw_message.get("payload", {})

            if msg_type == "subscribe":
                series_id = payload.get("series_id")
                if not series_id:
                    await ws_manager.send_error(websocket, "series_id is required")
                    continue

                # Unsubscribe from previous if any
                if subscription:
                    await ws_manager.disconnect(subscription)

                subscription = await ws_manager.subscribe(
                    websocket=websocket,
                    series_id=series_id,
                    viewer_mode=payload.get("viewer_mode", True),
                    player_id=payload.get("player_id"),
                    player_role=payload.get("player_role"),
                )

                await websocket.send_json(
                    {
                        "type": "subscribed",
                        "payload": {"series_id": series_id, "subscription_id": subscription.id},
                    }
                )

                # Send initial snapshot of current game state
                await ws_manager.send_initial_snapshot(websocket, series_id)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "payload": {}})

            elif msg_type == "set_audio":
                if subscription:
                    enabled = payload.get("enabled", False)
                    await ws_manager.set_audio_enabled(subscription.id, enabled)
                    await websocket.send_json(
                        {
                            "type": "audio_updated",
                            "payload": {"enabled": enabled},
                        }
                    )
                else:
                    await ws_manager.send_error(
                        websocket, "Must subscribe before setting audio preference"
                    )

            # Human player input messages
            elif msg_type == "human_speech":
                # Human submitted speech text (fallback or transcription)
                from websocket.voice_session import voice_session_manager

                series_id = payload.get("series_id")
                if series_id:
                    await voice_session_manager.handle_human_input(series_id, "speech", payload)

            elif msg_type == "human_vote":
                # Human submitted their vote
                from websocket.voice_session import voice_session_manager

                series_id = payload.get("series_id")
                if series_id:
                    await voice_session_manager.handle_human_input(series_id, "vote", payload)

            elif msg_type == "human_night_action":
                # Human submitted night action
                from websocket.voice_session import voice_session_manager

                series_id = payload.get("series_id")
                if series_id:
                    await voice_session_manager.handle_human_input(
                        series_id, "night_action", payload
                    )

            else:
                await ws_manager.send_error(websocket, f"Unknown message type: {msg_type}")

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    finally:
        if subscription:
            await ws_manager.disconnect(subscription)
