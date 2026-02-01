import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from db.database import get_db
from models.schemas import (
    Cheatsheet as CheatsheetSchema,
)
from models.schemas import (
    CheatsheetItem,
    PlayerCheatsheetResponse,
    to_utc_iso,
)

logger = logging.getLogger(__name__)

router = APIRouter()


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
            "created_at": to_utc_iso(cs.created_at),
            "created_after_game": cs.created_after_game,
        }
        for cs in cheatsheets
    ]
