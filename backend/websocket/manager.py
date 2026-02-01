"""WebSocket connection manager for live game streaming."""
import asyncio
import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from models.schemas import GameEvent, Visibility


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
        player_id: Optional[str] = None,
        player_role: Optional[str] = None,
    ):
        self.id = str(uuid4())
        self.websocket = websocket
        self.series_id = series_id
        self.viewer_mode = viewer_mode
        self.player_id = player_id
        self.player_role = player_role


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
                    s for s in self._subscriptions[subscription.series_id]
                    if s.id != subscription.id
                ]
                if not self._subscriptions[subscription.series_id]:
                    del self._subscriptions[subscription.series_id]

    async def subscribe(
        self,
        websocket: WebSocket,
        series_id: str,
        viewer_mode: bool = True,
        player_id: Optional[str] = None,
        player_role: Optional[str] = None,
    ) -> Subscription:
        """Subscribe a WebSocket to a series."""
        subscription = Subscription(
            websocket=websocket,
            series_id=series_id,
            viewer_mode=viewer_mode,
            player_id=player_id,
            player_role=player_role,
        )
        async with self._lock:
            if series_id not in self._subscriptions:
                self._subscriptions[series_id] = []
            self._subscriptions[series_id].append(subscription)
        return subscription

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
                    await self._send_message(sub.websocket, WSMessage(
                        type="event",
                        payload=event.model_dump(mode="json"),
                    ))
                except Exception:
                    # Connection might be closed
                    pass

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
            except Exception:
                pass

    async def broadcast_snapshot(
        self,
        series_id: str,
        game_id: str,
        alive_player_ids: list[str],
        phase: str,
        day_number: int,
        players: Optional[list[dict]] = None,
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
            except Exception:
                pass

    async def send_error(self, websocket: WebSocket, message: str, details: Optional[dict] = None) -> None:
        """Send an error message to a specific WebSocket."""
        await self._send_message(websocket, WSMessage(
            type="error",
            payload={"message": message, "details": details or {}},
        ))

    async def _send_message(self, websocket: WebSocket, message: WSMessage) -> None:
        """Send a message to a WebSocket."""
        await websocket.send_json(message.model_dump())


# Global connection manager instance
ws_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live game streaming."""
    await ws_manager.connect(websocket)
    subscription: Optional[Subscription] = None

    try:
        while True:
            data = await websocket.receive_json()

            msg_type = data.get("type")
            payload = data.get("payload", {})

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

                await websocket.send_json({
                    "type": "subscribed",
                    "payload": {"series_id": series_id, "subscription_id": subscription.id},
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "payload": {}})

            else:
                await ws_manager.send_error(websocket, f"Unknown message type: {msg_type}")

    except WebSocketDisconnect:
        pass
    finally:
        if subscription:
            await ws_manager.disconnect(subscription)
