"""API routes for Mafia ACE."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from db.database import get_db
from models.schemas import (
    Cheatsheet as CheatsheetSchema,
)
from models.schemas import (
    CheatsheetItem,
    GamePhase,
    GameResponse,
    ModelProvider,
    PlayerCheatsheetResponse,
    PlayerState,
    Role,
    SeriesConfig,
    SeriesResponse,
    SeriesStatus,
    Winner,
)

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
    from game.llm import get_available_providers

    # Validate that all requested providers have API keys configured
    available = set(get_available_providers())
    requested = {ModelProvider(p.model_provider) for p in config.players}
    missing = requested - available

    if missing:
        missing_str = ", ".join(p.value for p in missing)
        available_str = ", ".join(p.value for p in available) if available else "none"
        raise HTTPException(
            status_code=400,
            detail=f"Missing API keys for: {missing_str}. "
            f"Configure them in backend/.env. Available providers: {available_str}",
        )

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
            "ts": e.ts.isoformat(),
            "type": e.type,
            "visibility": e.visibility,
            "actor_player_id": e.actor_player_id,
            "target_player_id": e.target_player_id,
            "payload": e.payload,
        }
        for e in events
    ]


@router.get("/players/{player_id}/cheatsheet", response_model=PlayerCheatsheetResponse)
async def get_player_cheatsheet(
    player_id: str,
    game_number: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get the cheatsheet for a player.

    If game_number is provided, returns the cheatsheet that was in effect
    during that game (for replay mode). Otherwise returns the latest version.
    """
    player = await crud.get_player(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    if game_number is not None:
        cheatsheet = await crud.get_cheatsheet_at_game(db, player_id, game_number)
    else:
        cheatsheet = await crud.get_latest_cheatsheet(db, player_id)

    if not cheatsheet:
        raise HTTPException(status_code=404, detail="No cheatsheet found")

    # Parse cheatsheet items from JSON
    items = [CheatsheetItem.model_validate(item) for item in (cheatsheet.items or [])]

    return PlayerCheatsheetResponse(
        player_id=player.id,
        player_name=player.name,
        cheatsheet=CheatsheetSchema(
            items=items,
            version=cheatsheet.version,
        ),
        games_played=cheatsheet.created_after_game or 0,
    )


@router.get("/players/{player_id}/cheatsheet/history")
async def get_cheatsheet_history(
    player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all cheatsheet versions for a player."""
    player = await crud.get_player(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    cheatsheets = await crud.get_cheatsheet_history(db, player_id)
    return [
        {
            "version": cs.version,
            "items": cs.items,
            "created_at": cs.created_at.isoformat(),
            "created_after_game": cs.created_after_game,
        }
        for cs in cheatsheets
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
