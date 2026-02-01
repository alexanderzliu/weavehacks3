from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.games import router as games_router
from api.players import router as players_router
from api.series import router as series_router
from config import get_settings
from db import crud
from db.database import get_db
from game.llm import get_available_providers
from models.schemas import ModelProvider

router = APIRouter()

router.include_router(series_router, tags=["series"])
router.include_router(games_router, tags=["games"])
router.include_router(players_router, tags=["players"])


@router.get("/providers", tags=["config"])
async def get_providers_config():
    """Return available providers with their default models."""
    settings = get_settings()
    available = set(get_available_providers())

    # Map providers to their default models from settings
    provider_models = {
        ModelProvider.ANTHROPIC: settings.ANTHROPIC_MODEL,
        ModelProvider.OPENAI: settings.OPENAI_MODEL,
        ModelProvider.GOOGLE: settings.GOOGLE_MODEL,
        ModelProvider.OPENAI_COMPATIBLE: settings.OPENAI_COMPATIBLE_MODEL,
        ModelProvider.OPENROUTER: settings.OPENROUTER_MODEL,
        ModelProvider.WANDB: "qwen3-235b",  # W&B has curated list, use default
    }

    return {
        "providers": [
            {
                "id": p.value,
                "available": p in available,
                "default_model": provider_models.get(p, ""),
            }
            for p in ModelProvider
        ]
    }


# ============ Voice Session Routes ============


@router.post("/series/{series_id}/join-voice", tags=["voice"])
async def join_voice_session(
    series_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Join a series as the human player with voice.

    Creates a Daily room for voice communication and returns
    the room URL and token for the client to connect.
    """
    from websocket.voice_session import voice_session_manager

    series = await crud.get_series(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Find human player in series
    players = await crud.get_players_for_series(db, series_id)
    human_player = next((p for p in players if getattr(p, "is_human", False)), None)

    if not human_player:
        raise HTTPException(
            status_code=400,
            detail="No human player slot in this series",
        )

    # Create or get voice session
    session = await voice_session_manager.create_session(
        series_id=series_id,
        player_id=human_player.id,
        player_name=human_player.name,
    )

    return {
        "session_id": session.session_id,
        "player_id": session.player_id,
        "player_name": session.player_name,
        "room_url": session.room_url,
        "room_token": session.room_token,
    }


@router.delete("/series/{series_id}/voice-session", tags=["voice"])
async def leave_voice_session(
    series_id: str,
):
    """Leave a voice session."""
    from websocket.voice_session import voice_session_manager

    await voice_session_manager.destroy_session(series_id)
    return {"message": "Voice session ended"}
