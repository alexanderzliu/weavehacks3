import weave
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from db.database import init_db
from api.routes import router as api_router
from websocket.manager import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    if settings.WANDB_API_KEY:
        try:
            weave.init(settings.WEAVE_PROJECT)
        except Exception as e:
            print(f"Warning: Weave initialization failed: {e}")
    yield
    # Shutdown
    pass


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
