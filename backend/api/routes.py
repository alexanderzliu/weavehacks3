from fastapi import APIRouter

from api.games import router as games_router
from api.players import router as players_router
from api.series import router as series_router

router = APIRouter()

router.include_router(series_router, tags=["series"])
router.include_router(games_router, tags=["games"])
router.include_router(players_router, tags=["players"])
