import os
from pathlib import Path

# === DEBUG: Understanding the environment ===
print(f"[DEBUG] Current working directory: {os.getcwd()}")
print(f"[DEBUG] .env exists in cwd: {Path('.env').exists()}")
print(f"[DEBUG] WANDB_API_KEY in os.environ before settings: {os.environ.get('WANDB_API_KEY', '(not set)')[:20]}...")

from config import get_settings

settings = get_settings()

print(f"[DEBUG] settings.WANDB_API_KEY: {settings.WANDB_API_KEY[:20] if settings.WANDB_API_KEY else '(empty)'}...")
print(f"[DEBUG] settings.WEAVE_ENTITY: {settings.WEAVE_ENTITY}")
print(f"[DEBUG] settings.WEAVE_PROJECT: {settings.WEAVE_PROJECT}")

# Set WANDB_API_KEY before importing weave (it checks auth on import)
if settings.WANDB_API_KEY:
    os.environ["WANDB_API_KEY"] = settings.WANDB_API_KEY
    print(f"[DEBUG] Set os.environ WANDB_API_KEY to: {os.environ['WANDB_API_KEY'][:20]}...")
else:
    print("[DEBUG] WARNING: settings.WANDB_API_KEY is empty, not setting env var")

import weave
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db
from db import redis_cache
from api.routes import router as api_router
from websocket.manager import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    if settings.WANDB_API_KEY:
        try:
            weave_project = f"{settings.WEAVE_ENTITY}/{settings.WEAVE_PROJECT}"
            weave.init(weave_project)
            print(f"Weave initialized: {weave_project}")
        except Exception as e:
            print(f"Warning: Weave initialization failed: {e}")
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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
