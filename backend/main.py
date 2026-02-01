import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Debug environment state before loading settings
logger.debug("Current working directory: %s", os.getcwd())
logger.debug(".env exists in cwd: %s", Path(".env").exists())
logger.debug(
    "WANDB_API_KEY in os.environ before settings: %s...",
    os.environ.get("WANDB_API_KEY", "(not set)")[:20],
)

from config import get_settings

settings = get_settings()

logger.debug(
    "settings.WANDB_API_KEY: %s...",
    settings.WANDB_API_KEY[:20] if settings.WANDB_API_KEY else "(empty)",
)
logger.debug("settings.WEAVE_ENTITY: %s", settings.WEAVE_ENTITY)
logger.debug("settings.WEAVE_PROJECT: %s", settings.WEAVE_PROJECT)

# Set WANDB_API_KEY before importing weave (it checks auth on import)
if settings.WANDB_API_KEY:
    os.environ["WANDB_API_KEY"] = settings.WANDB_API_KEY
    logger.debug("Set os.environ WANDB_API_KEY to: %s...", os.environ["WANDB_API_KEY"][:20])
else:
    logger.warning("WANDB_API_KEY is empty, Weave tracing will be disabled")

from contextlib import asynccontextmanager

import weave
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router as api_router
from db import redis_cache
from db.database import init_db
from websocket.manager import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()

    # Check for AI provider configuration
    from game.llm import get_available_providers

    available = get_available_providers()
    if not available:
        logger.warning(
            "No AI provider API keys configured! "
            "Set at least one in backend/.env: OPENAI_API_KEY, ANTHROPIC_API_KEY, "
            "GOOGLE_API_KEY (or GEMINI_API_KEY), OPENAI_COMPATIBLE_BASE_URL + OPENAI_COMPATIBLE_API_KEY, "
            "or OPENROUTER_API_KEY"
        )
    else:
        providers_str = ", ".join(p.value for p in available)
        logger.info("AI providers available: %s", providers_str)

    if settings.WANDB_API_KEY:
        try:
            weave_project = f"{settings.WEAVE_ENTITY}/{settings.WEAVE_PROJECT}"
            weave.init(weave_project)
            logger.info("Weave initialized: %s", weave_project)
        except Exception as e:
            logger.warning("Weave initialization failed: %s", e)
    yield
    # Shutdown
    await redis_cache.close_redis()


app = FastAPI(
    title="Mafia ACE API",
    description="AI agents playing Mafia with self-improving cheatsheets",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(ws_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Log validation errors with context before returning 422."""
    errors = exc.errors()
    detail_message = _format_validation_errors(list(errors))
    logger.warning(
        "Request validation failed: %s %s",
        request.method,
        request.url.path,
        extra={
            "errors": errors,
            "body": exc.body if hasattr(exc, "body") else None,
        },
    )
    # Log each error in a readable format
    for err in errors:
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Unknown error")
        logger.warning("  Validation error in '%s': %s", field, msg)

    return JSONResponse(
        status_code=422,
        content={"detail": detail_message, "errors": errors},
    )


def _format_validation_errors(errors: list[dict]) -> str:
    if not errors:
        return "Request validation failed"
    parts = []
    for err in errors:
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        if field:
            parts.append(f"{field}: {msg}")
        else:
            parts.append(msg)
    return "; ".join(parts)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(
        "HTTP %s %s -> %s: %s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.get("/health")
async def health_check():
    from game.llm import get_available_providers

    available = get_available_providers()
    return {
        "status": "healthy",
        "providers": [p.value for p in available],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
