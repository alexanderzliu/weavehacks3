"""Series orchestrator - runs N games with reflection between each."""
import asyncio
from datetime import datetime
from typing import Optional
from uuid import uuid4

import weave
from weave.trace.weave_client import Call

from db.database import get_db_session
from db import crud
from game.runner import GameRunner, assign_roles
from game.voice_runner import VoiceGameRunner
from game.human_adapter import HumanPlayerAdapter
from game.reflection import ReflectionPipeline
from models.schemas import (
    SeriesStatus,
    GamePhase,
    GameEvent,
    EventType,
    Visibility,
    ModelProvider,
)
from websocket.manager import ws_manager
from websocket.voice_session import voice_session_manager


def _series_display_name(call: Call) -> str:
    """Generate trace name: {series_name}-{yyyy-mm-dd}-{HH:MM}"""
    series_name = call.inputs.get("series_name", "series")
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    return f"{series_name}-{timestamp}"


@weave.op(call_display_name=_series_display_name)
async def run_series(series_id: str, series_name: str = "series") -> None:
    """Run a complete series of games with reflection."""
    # Load series data
    async with get_db_session() as db:
        series = await crud.get_series_with_games(db, series_id)
        if not series:
            raise ValueError(f"Series {series_id} not found")

        players = await crud.get_players_for_series(db, series_id)

    total_games = series.total_games
    base_seed = series.random_seed

    # Broadcast initial status
    await ws_manager.broadcast_series_status(
        series_id,
        SeriesStatus.IN_PROGRESS.value,
        0,
        total_games,
    )

    try:
        for game_number in range(1, total_games + 1):
            # Check for stop request
            async with get_db_session() as db:
                series = await crud.get_series(db, series_id)
                if series.status == SeriesStatus.STOP_REQUESTED.value:
                    break

            # Update current game number
            async with get_db_session() as db:
                await crud.update_series_status(
                    db, series_id,
                    SeriesStatus.IN_PROGRESS,
                    current_game_number=game_number,
                )

            await ws_manager.broadcast_series_status(
                series_id,
                SeriesStatus.IN_PROGRESS.value,
                game_number,
                total_games,
            )

            # Create game
            game_seed = base_seed + game_number if base_seed else None
            async with get_db_session() as db:
                game = await crud.create_game(db, series_id, game_number, game_seed)
                game_id = game.id

            # Assign roles
            player_ids = [p.id for p in players]

            # Build fixed_roles map from series config
            config_players = series.config.get("players", [])
            player_name_to_id = {p.name: p.id for p in players}
            fixed_roles = {}
            for pc in config_players:
                if pc.get("fixed_role"):
                    pid = player_name_to_id.get(pc["name"])
                    if pid:
                        fixed_roles[pid] = pc["fixed_role"]

            await assign_roles(game_id, player_ids, fixed_roles, game_seed)

            # Check if any player is human
            human_player = next(
                (p for p in players if p.is_human),
                None
            )

            # Create appropriate runner
            if human_player:
                # Create human adapter with WebSocket notification callback
                async def ws_notify(msg_type: str, payload: dict):
                    await ws_manager.send_to_player(
                        series_id, human_player.id, msg_type, payload
                    )

                human_adapter = HumanPlayerAdapter(
                    player_id=human_player.id,
                    player_name=human_player.name,
                    ws_notify=ws_notify,
                )
                voice_session_manager.set_adapter(series_id, human_adapter)

                runner = VoiceGameRunner(
                    game_id, series_id, human_adapter, game_seed
                )
            else:
                runner = GameRunner(game_id, series_id, game_seed)

            winner = await runner.run()

            # Check for stop request before reflection
            async with get_db_session() as db:
                series = await crud.get_series(db, series_id)
                stop_after_reflection = series.status == SeriesStatus.STOP_REQUESTED.value

            # Run reflection for each player
            await run_reflections(series_id, game_id, game_number, winner.value)

            if stop_after_reflection:
                break

        # Mark series complete
        async with get_db_session() as db:
            await crud.update_series_status(db, series_id, SeriesStatus.COMPLETED)

        await ws_manager.broadcast_series_status(
            series_id,
            SeriesStatus.COMPLETED.value,
            game_number,
            total_games,
        )

    except Exception as e:
        # Log error but don't crash
        async with get_db_session() as db:
            event = GameEvent(
                id=str(uuid4()),
                series_id=series_id,
                game_id=series_id,  # Use series_id for series-level errors
                type=EventType.ERROR,
                visibility=Visibility.VIEWER,
                payload={"error": str(e), "phase": "series"},
            )
            await crud.create_game_event(db, event)

        await ws_manager.broadcast_event(series_id, event)

        # Mark as completed (with error)
        async with get_db_session() as db:
            await crud.update_series_status(db, series_id, SeriesStatus.COMPLETED)


async def run_reflections(
    series_id: str,
    game_id: str,
    game_number: int,
    winner: str,
) -> None:
    """Run reflection pipeline for all players after a game."""
    pipeline = ReflectionPipeline(series_id, game_id, game_number)

    # Get game players with their final state
    async with get_db_session() as db:
        game_players = await crud.get_game_players(db, game_id)

    async def reflect_player(gp):
        """Run reflection for a single player with error handling."""
        try:
            await pipeline.run_for_player(
                player_id=gp.player.id,
                player_name=gp.player.name,
                role=gp.role,
                survived=gp.is_alive,
                winner=winner,
                model_provider=ModelProvider(gp.player.model_provider),
                model_name=gp.player.model_name,
            )
        except Exception as e:
            # Log but continue with other players
            event = GameEvent(
                id=str(uuid4()),
                series_id=series_id,
                game_id=game_id,
                type=EventType.ERROR,
                visibility=Visibility.VIEWER,
                actor_id=gp.player.id,
                payload={"error": str(e), "phase": "reflection"},
            )
            async with get_db_session() as db:
                await crud.create_game_event(db, event)
            await ws_manager.broadcast_event(series_id, event)

    # Run all reflections in parallel
    await asyncio.gather(*[reflect_player(gp) for gp in game_players])
