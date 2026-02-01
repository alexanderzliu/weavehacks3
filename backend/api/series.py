import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from db.database import get_db
from models.schemas import (
    ModelProvider,
    SeriesConfig,
    SeriesResponse,
    SeriesStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Store for running series tasks
_running_series: dict[str, asyncio.Task] = {}


@router.post("/series", response_model=SeriesResponse)
async def create_series(
    config: SeriesConfig,
    random_seed: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Create a new series with players and initial cheatsheets."""
    # Log incoming request for debugging
    logger.info(
        "create_series request",
        extra={
            "series_name": config.name,
            "total_games": config.total_games,
            "player_count": len(config.players),
            "providers": [p.model_provider for p in config.players],
            "random_seed": random_seed,
        },
    )

    from game.llm import get_available_providers

    # Validate that all requested providers have API keys configured
    available = set(get_available_providers())
    requested = {ModelProvider(p.model_provider) for p in config.players}
    missing = requested - available

    if missing:
        missing_str = ", ".join(p.value for p in missing)
        available_str = ", ".join(p.value for p in available) if available else "none"
        error_detail = (
            f"Missing API keys for: {missing_str}. "
            f"Configure them in backend/.env. Available providers: {available_str}"
        )
        logger.warning(
            "Series creation failed - missing API keys",
            extra={
                "missing_providers": [p.value for p in missing],
                "available_providers": [p.value for p in available],
                "series_name": config.name,
            },
        )
        raise HTTPException(status_code=400, detail=error_detail)

    try:
        series = await crud.create_series(db, config, random_seed)
        await db.commit()

        return SeriesResponse(
            id=series.id,
            name=series.name,
            status=SeriesStatus(series.status),
            total_games=series.total_games,
            current_game_number=series.current_game_number,
            config=config,
            created_at=series.created_at,
        )
    except Exception as e:
        logger.error(
            "Database error creating series",
            extra={"error": str(e), "series_name": config.name},
            exc_info=True,
        )
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error creating series") from e


@router.post("/series/{series_id}/start")
async def start_series(
    series_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Start running a series asynchronously."""
    series = await crud.get_series(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    if series.status != SeriesStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Series is already {series.status}, cannot start",
        )

    # Import here to avoid circular imports
    from game.orchestrator import run_series
    from websocket.manager import ws_manager

    # Update status
    await crud.update_series_status(db, series_id, SeriesStatus.IN_PROGRESS)
    await db.commit()

    # Start series in background
    task = asyncio.create_task(run_series(series_id, series.name, broadcaster=ws_manager))
    _running_series[series_id] = task

    return {"message": "Series started", "series_id": series_id}


@router.post("/series/{series_id}/stop")
async def stop_series(
    series_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Request to stop a series after the current phase/game."""
    from websocket.manager import ws_manager

    series = await crud.get_series(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    if series.status != SeriesStatus.IN_PROGRESS.value:
        raise HTTPException(
            status_code=400,
            detail=f"Series is {series.status}, cannot stop",
        )

    await crud.update_series_status(db, series_id, SeriesStatus.STOP_REQUESTED)
    await db.commit()

    # Broadcast stop_requested immediately so frontend can show "Stopping..." state
    await ws_manager.broadcast_series_status(
        series_id,
        SeriesStatus.STOP_REQUESTED.value,
        series.current_game_number,
        series.total_games,
    )

    return {"message": "Stop requested", "series_id": series_id}


@router.get("/series/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get series status and info."""
    series = await crud.get_series(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    return SeriesResponse(
        id=series.id,
        name=series.name,
        status=SeriesStatus(series.status),
        total_games=series.total_games,
        current_game_number=series.current_game_number,
        config=SeriesConfig.model_validate(series.config),
        created_at=series.created_at,
    )


@router.get("/series")
async def list_series(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List recent series."""
    series_list = await crud.list_series(db, limit)
    return [
        SeriesResponse(
            id=s.id,
            name=s.name,
            status=SeriesStatus(s.status),
            total_games=s.total_games,
            current_game_number=s.current_game_number,
            config=SeriesConfig.model_validate(s.config),
            created_at=s.created_at,
        )
        for s in series_list
    ]


@router.get("/series/{series_id}/players")
async def get_series_players(
    series_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all players in a series."""
    series = await crud.get_series(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    players = await crud.get_players_for_series(db, series_id)
    return [
        {
            "id": p.id,
            "name": p.name,
            "model_provider": p.model_provider,
            "model_name": p.model_name,
        }
        for p in players
    ]


@router.get("/series/{series_id}/games")
async def get_series_games(
    series_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all games in a series."""
    series = await crud.get_series(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    games = await crud.get_games_for_series(db, series_id)
    return [
        {
            "id": g.id,
            "game_number": g.game_number,
            "status": g.status,
            "winner": g.winner,
            "day_number": g.day_number,
            "started_at": g.started_at.isoformat() if g.started_at else None,
            "completed_at": g.completed_at.isoformat() if g.completed_at else None,
        }
        for g in games
    ]
