import subprocess
import sys
from pathlib import Path

from app.utils.logging import get_logger
from app.config import get_settings
from app.ml.model_store import ModelStore

logger = get_logger(__name__)
settings = get_settings()


async def init_database() -> None:
    """Run Alembic migrations and optionally seed the database."""
    logger.info("Running database migrations...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        if result.returncode != 0:
            logger.error(f"Migration failed: {result.stderr}")
        else:
            logger.info("Migrations applied successfully.")
    except Exception as e:
        logger.error(f"Migration error: {e}")

    # Ensure DB/model/predictions are usable even with partially initialized data.
    await ensure_runtime_state()


async def maybe_seed_database() -> None:
    """Seed or repair DB state so predictions can be served."""
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.models.team import Team
    from app.models.match import Match
    from app.models.prediction import Prediction

    async with AsyncSessionLocal() as session:
        team_count = await session.scalar(select(func.count()).select_from(Team)) or 0
        match_count = await session.scalar(select(func.count()).select_from(Match)) or 0
        prediction_count = await session.scalar(select(func.count()).select_from(Prediction)) or 0

    model_exists = ModelStore().load_latest()[0] is not None

    if team_count == 0 or match_count == 0:
        logger.info("Empty database detected. Starting historical data seed...")
        try:
            from app.services.data_sync import DataSyncService
            sync_service = DataSyncService()
            await sync_service.seed_historical_data()
        except Exception as e:
            logger.error(f"Seed failed: {e}", exc_info=True)
            return

    if team_count > 0 and match_count > 0:
        logger.info(
            "Existing database detected (teams=%s, matches=%s, predictions=%s). "
            "Ensuring model and predictions are available...",
            team_count, match_count, prediction_count
        )

    try:
        from app.services.elo_service import EloService
        elo_service = EloService()
        await elo_service.recompute_all()
    except Exception as e:
        logger.error(f"Elo recompute failed during bootstrap: {e}", exc_info=True)

    if not model_exists:
        try:
            logger.info("No trained model found. Training model...")
            from app.ml.trainer import ModelTrainer
            trainer = ModelTrainer()
            await trainer.train()
        except Exception as e:
            logger.error(f"Model training failed during bootstrap: {e}", exc_info=True)

    try:
        if prediction_count == 0:
            logger.info("No predictions found. Generating upcoming predictions...")
        else:
            logger.info("Refreshing upcoming predictions (existing=%s)...", prediction_count)

        from app.services.prediction_service import PredictionService
        pred_service = PredictionService()
        await pred_service.generate_upcoming_predictions()
        await pred_service.resolve_predictions()
        logger.info("Database bootstrap/repair complete.")
    except Exception as e:
        logger.error(f"Prediction generation failed during bootstrap: {e}", exc_info=True)


async def ensure_initial_sync_if_needed() -> None:
    """
    Perform a quick fixture/results sync when database is missing core records.
    Keeps startup resilient when an older DB exists but is stale.
    """
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.models.match import Match

    async with AsyncSessionLocal() as session:
        match_count = await session.scalar(select(func.count()).select_from(Match)) or 0

    if match_count > 0:
        return

    logger.info("No matches found after bootstrap. Running initial sync.")
    try:
        from app.services.data_sync import DataSyncService
        sync_service = DataSyncService()
        await sync_service.sync_upcoming_fixtures()
        await sync_service.sync_recent_results()
    except Exception as e:
        logger.error(f"Initial sync failed: {e}", exc_info=True)


async def ensure_runtime_state() -> None:
    """
    Run a lightweight startup consistency routine so dashboards are never empty.
    """
    await maybe_seed_database()
    await ensure_initial_sync_if_needed()

    # Re-check model after bootstrap/repair and train if still absent.
    predictor, _ = ModelStore().load_latest()
    if predictor is not None:
        return

    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.models.match import Match, MatchStatus

    async with AsyncSessionLocal() as session:
        finished_count = await session.scalar(
            select(func.count()).select_from(Match).where(Match.status == MatchStatus.FINISHED)
        ) or 0

    if finished_count < settings.min_training_samples:
        logger.info(
            "Model still unavailable after startup checks; using Elo fallback "
            "(finished matches=%s, required=%s).",
            finished_count,
            settings.min_training_samples,
        )
        return

    try:
        from app.ml.trainer import ModelTrainer
        trainer = ModelTrainer()
        await trainer.train()
    except Exception as e:
        logger.error(f"Recovery training failed: {e}", exc_info=True)
