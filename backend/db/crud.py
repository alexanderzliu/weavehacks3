"""CRUD operations for database models."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Series, Player, Game, GamePlayer, Cheatsheet, GameEvent
from models.schemas import (
    SeriesConfig,
    PlayerConfig,
    GameEvent as GameEventSchema,
    Cheatsheet as CheatsheetSchema,
    SeriesStatus,
    GamePhase,
)


# ============ Series CRUD ============

async def create_series(
    db: AsyncSession,
    config: SeriesConfig,
    random_seed: Optional[int] = None,
) -> Series:
    """Create a new series with players and initial cheatsheets."""
    series_id = str(uuid4())

    series = Series(
        id=series_id,
        name=config.name,
        status=SeriesStatus.PENDING.value,
        total_games=config.total_games,
        current_game_number=0,
        config=config.model_dump(),
        random_seed=random_seed,
    )
    db.add(series)

    # Create players and their initial cheatsheets
    for player_config in config.players:
        player_id = str(uuid4())
        player = Player(
            id=player_id,
            series_id=series_id,
            name=player_config.name,
            model_provider=player_config.model_provider.value,
            model_name=player_config.model_name,
        )
        db.add(player)

        # Create version 0 cheatsheet
        initial_items = []
        if player_config.initial_cheatsheet:
            initial_items = [item.model_dump() for item in player_config.initial_cheatsheet.items]

        cheatsheet = Cheatsheet(
            id=str(uuid4()),
            player_id=player_id,
            version=0,
            items=initial_items,
            created_after_game=None,
        )
        db.add(cheatsheet)

    await db.flush()
    return series


async def get_series(db: AsyncSession, series_id: str) -> Optional[Series]:
    """Get series by ID with players loaded."""
    result = await db.execute(
        select(Series)
        .options(selectinload(Series.players))
        .where(Series.id == series_id)
    )
    return result.scalar_one_or_none()


async def get_series_with_games(db: AsyncSession, series_id: str) -> Optional[Series]:
    """Get series by ID with players and games loaded."""
    result = await db.execute(
        select(Series)
        .options(selectinload(Series.players), selectinload(Series.games))
        .where(Series.id == series_id)
    )
    return result.scalar_one_or_none()


async def update_series_status(
    db: AsyncSession,
    series_id: str,
    status: SeriesStatus,
    current_game_number: Optional[int] = None,
) -> None:
    """Update series status and optionally current game number."""
    values = {"status": status.value, "updated_at": datetime.utcnow()}
    if current_game_number is not None:
        values["current_game_number"] = current_game_number

    await db.execute(
        update(Series).where(Series.id == series_id).values(**values)
    )


async def list_series(db: AsyncSession, limit: int = 50) -> list[Series]:
    """List recent series."""
    result = await db.execute(
        select(Series)
        .options(selectinload(Series.players))
        .order_by(Series.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ============ Player CRUD ============

async def get_players_for_series(db: AsyncSession, series_id: str) -> list[Player]:
    """Get all players for a series."""
    result = await db.execute(
        select(Player).where(Player.series_id == series_id)
    )
    return list(result.scalars().all())


async def get_player(db: AsyncSession, player_id: str) -> Optional[Player]:
    """Get player by ID."""
    result = await db.execute(select(Player).where(Player.id == player_id))
    return result.scalar_one_or_none()


# ============ Game CRUD ============

async def create_game(
    db: AsyncSession,
    series_id: str,
    game_number: int,
    random_seed: Optional[int] = None,
) -> Game:
    """Create a new game."""
    game = Game(
        id=str(uuid4()),
        series_id=series_id,
        game_number=game_number,
        status=GamePhase.PENDING.value,
        random_seed=random_seed,
    )
    db.add(game)
    await db.flush()
    return game


async def get_game(db: AsyncSession, game_id: str) -> Optional[Game]:
    """Get game by ID with game_players loaded."""
    result = await db.execute(
        select(Game)
        .options(selectinload(Game.game_players).selectinload(GamePlayer.player))
        .where(Game.id == game_id)
    )
    return result.scalar_one_or_none()


async def update_game(
    db: AsyncSession,
    game_id: str,
    status: Optional[GamePhase] = None,
    winner: Optional[str] = None,
    day_number: Optional[int] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
) -> None:
    """Update game fields."""
    values = {}
    if status is not None:
        values["status"] = status.value
    if winner is not None:
        values["winner"] = winner
    if day_number is not None:
        values["day_number"] = day_number
    if started_at is not None:
        values["started_at"] = started_at
    if completed_at is not None:
        values["completed_at"] = completed_at

    if values:
        await db.execute(update(Game).where(Game.id == game_id).values(**values))


async def get_games_for_series(db: AsyncSession, series_id: str) -> list[Game]:
    """Get all games for a series."""
    result = await db.execute(
        select(Game)
        .where(Game.series_id == series_id)
        .order_by(Game.game_number)
    )
    return list(result.scalars().all())


async def get_active_game_for_series(db: AsyncSession, series_id: str) -> Optional[Game]:
    """Get the currently active (non-completed) game for a series."""
    result = await db.execute(
        select(Game)
        .options(selectinload(Game.game_players).selectinload(GamePlayer.player))
        .where(Game.series_id == series_id)
        .where(Game.status != "completed")
        .order_by(Game.game_number.desc())
    )
    return result.scalar_one_or_none()


# ============ GamePlayer CRUD ============

async def create_game_player(
    db: AsyncSession,
    game_id: str,
    player_id: str,
    role: str,
) -> GamePlayer:
    """Create a game player assignment."""
    gp = GamePlayer(
        id=str(uuid4()),
        game_id=game_id,
        player_id=player_id,
        role=role,
        is_alive=True,
    )
    db.add(gp)
    await db.flush()
    return gp


async def get_game_players(db: AsyncSession, game_id: str) -> list[GamePlayer]:
    """Get all game players for a game with player info."""
    result = await db.execute(
        select(GamePlayer)
        .options(selectinload(GamePlayer.player))
        .where(GamePlayer.game_id == game_id)
    )
    return list(result.scalars().all())


async def update_game_player(
    db: AsyncSession,
    game_player_id: str,
    is_alive: Optional[bool] = None,
    eliminated_day: Optional[int] = None,
    elimination_type: Optional[str] = None,
) -> None:
    """Update game player state."""
    values = {}
    if is_alive is not None:
        values["is_alive"] = is_alive
    if eliminated_day is not None:
        values["eliminated_day"] = eliminated_day
    if elimination_type is not None:
        values["elimination_type"] = elimination_type

    if values:
        await db.execute(
            update(GamePlayer).where(GamePlayer.id == game_player_id).values(**values)
        )


# ============ Cheatsheet CRUD ============

async def get_latest_cheatsheet(db: AsyncSession, player_id: str) -> Optional[Cheatsheet]:
    """Get the most recent cheatsheet version for a player."""
    result = await db.execute(
        select(Cheatsheet)
        .where(Cheatsheet.player_id == player_id)
        .order_by(Cheatsheet.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_cheatsheet_version(
    db: AsyncSession,
    player_id: str,
    items: list[dict],
    game_number: int,
) -> Cheatsheet:
    """Create a new cheatsheet version."""
    # Get current version
    current = await get_latest_cheatsheet(db, player_id)
    new_version = (current.version + 1) if current else 0

    cheatsheet = Cheatsheet(
        id=str(uuid4()),
        player_id=player_id,
        version=new_version,
        items=items,
        created_after_game=game_number,
    )
    db.add(cheatsheet)
    await db.flush()
    return cheatsheet


async def get_cheatsheet_history(db: AsyncSession, player_id: str) -> list[Cheatsheet]:
    """Get all cheatsheet versions for a player."""
    result = await db.execute(
        select(Cheatsheet)
        .where(Cheatsheet.player_id == player_id)
        .order_by(Cheatsheet.version)
    )
    return list(result.scalars().all())


async def get_cheatsheet_at_game(
    db: AsyncSession,
    player_id: str,
    game_number: int,
) -> Optional[Cheatsheet]:
    """Get the cheatsheet that was in effect during a specific game.

    During Game N, the player uses the cheatsheet with the highest version
    where created_after_game is NULL (initial) or < N.
    """
    from sqlalchemy import or_

    result = await db.execute(
        select(Cheatsheet)
        .where(Cheatsheet.player_id == player_id)
        .where(
            or_(
                Cheatsheet.created_after_game.is_(None),
                Cheatsheet.created_after_game < game_number,
            )
        )
        .order_by(Cheatsheet.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ============ GameEvent CRUD ============

async def create_game_event(db: AsyncSession, event: GameEventSchema) -> GameEvent:
    """Create a game event."""
    db_event = GameEvent(
        id=event.id,
        series_id=event.series_id,
        game_id=event.game_id,
        ts=event.ts,
        type=event.type.value,
        visibility=event.visibility.value,
        actor_player_id=event.actor_id,
        target_player_id=event.target_id,
        payload=event.payload,
    )
    db.add(db_event)
    await db.flush()
    return db_event


async def get_game_events(
    db: AsyncSession,
    game_id: str,
    visibility_filter: Optional[list[str]] = None,
) -> list[GameEvent]:
    """Get events for a game, optionally filtered by visibility."""
    query = select(GameEvent).where(GameEvent.game_id == game_id)

    if visibility_filter:
        query = query.where(GameEvent.visibility.in_(visibility_filter))

    query = query.order_by(GameEvent.ts)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_events_for_player(
    db: AsyncSession,
    game_id: str,
    player_id: str,
    player_role: str,
) -> list[GameEvent]:
    """Get events visible to a specific player based on their role."""
    # Determine which visibilities this player can see
    visible = ["public"]
    if player_role == "mafia":
        visible.append("mafia")

    query = select(GameEvent).where(
        GameEvent.game_id == game_id,
        (
            GameEvent.visibility.in_(visible) |
            ((GameEvent.visibility == "private") & (GameEvent.actor_player_id == player_id))
        )
    ).order_by(GameEvent.ts)

    result = await db.execute(query)
    return list(result.scalars().all())
