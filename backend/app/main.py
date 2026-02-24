import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.utils.logging import setup_logging, get_logger

settings = get_settings()
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting OctoPredict backend...")

    # Ensure data directory exists
    os.makedirs("./data/models", exist_ok=True)

    # Run DB migrations
    from app.db.init_db import init_database
    await init_database()

    # Start scheduler
    from app.scheduler.jobs import start_scheduler
    scheduler = await start_scheduler()

    logger.info("OctoPredict backend ready.")
    yield

    # Shutdown
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("OctoPredict backend stopped.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="OctoPredict API",
        description="Football match prediction platform with XGBoost + Elo ratings",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from app.api.v1 import matches, predictions, teams, leagues, stats
    app.include_router(matches.router, prefix="/api/v1")
    app.include_router(predictions.router, prefix="/api/v1")
    app.include_router(teams.router, prefix="/api/v1")
    app.include_router(leagues.router, prefix="/api/v1")
    app.include_router(stats.router, prefix="/api/v1")

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
