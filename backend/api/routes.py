from fastapi import APIRouter

from api.games import router as games_router
from api.players import router as players_router
from api.series import router as series_router
from config import get_settings
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
