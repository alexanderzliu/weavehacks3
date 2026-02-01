import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from db.database import get_db
from models.schemas import (
    GamePhase,
    GameResponse,
    ModelProvider,
    PlayerState,
    Role,
    Winner,
    to_utc_iso,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get game details."""
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    players = [
        PlayerState(
            id=gp.player.id,
            name=gp.player.name,
            model_provider=ModelProvider(gp.player.model_provider),
            model_name=gp.player.model_name,
            role=Role(gp.role) if gp.role else None,
            is_alive=gp.is_alive,
        )
        for gp in game.game_players
    ]

    return GameResponse(
        id=game.id,
        series_id=game.series_id,
        game_number=game.game_number,
        status=GamePhase(game.status),
        winner=Winner(game.winner) if game.winner else None,
        players=players,
        day_number=game.day_number,
        started_at=game.started_at,
        completed_at=game.completed_at,
    )


@router.get("/games/{game_id}/events")
async def get_game_events(
    game_id: str,
    viewer_mode: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Get events for a game. Viewer mode includes all events."""
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if viewer_mode:
        # Viewers see everything
        events = await crud.get_game_events(db, game_id)
    else:
        # Non-viewer mode only sees public events
        events = await crud.get_game_events(db, game_id, visibility_filter=["public"])

    return [
        {
            "id": e.id,
            "ts": to_utc_iso(e.ts),
            "type": e.type,
            "visibility": e.visibility,
            "actor_player_id": e.actor_player_id,
            "target_player_id": e.target_player_id,
            "payload": e.payload,
        }
        for e in events
    ]
