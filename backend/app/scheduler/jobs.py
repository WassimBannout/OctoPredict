"""
APScheduler job definitions.

Jobs:
  sync_fixtures      - 06:00, 18:00 UTC
  sync_results       - Every 2 hours
  retrain_model      - Monday 03:00 UTC
  generate_preds     - 07:00 UTC daily

All jobs log to job_logs table.
"""
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import AsyncSessionLocal
from app.models.job_log import JobLog
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def _log_job(name: str, status: str, count: int, error: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        log = JobLog(
            job_name=name,
            status=status,
            records_processed=count,
            error_message=error,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        session.add(log)
        await session.commit()


async def job_sync_fixtures() -> None:
    logger.info("[scheduler] sync_fixtures starting...")
    try:
        from app.services.data_sync import DataSyncService
        service = DataSyncService()
        count = await service.sync_upcoming_fixtures()
        await _log_job("sync_fixtures", "success", count)
        logger.info(f"[scheduler] sync_fixtures done: {count} matches.")
    except Exception as e:
        logger.error(f"[scheduler] sync_fixtures failed: {e}", exc_info=True)
        await _log_job("sync_fixtures", "error", 0, str(e))


async def job_sync_results() -> None:
    logger.info("[scheduler] sync_results starting...")
    try:
        from app.services.data_sync import DataSyncService
        from app.services.prediction_service import PredictionService
        from app.services.elo_service import EloService

        sync = DataSyncService()
        updated = await sync.sync_recent_results()

        if updated > 0:
            elo = EloService()
            await elo.recompute_all()

            pred = PredictionService()
            resolved = await pred.resolve_predictions()
            logger.info(f"[scheduler] Resolved {resolved} predictions.")

        await _log_job("sync_results", "success", updated)
        logger.info(f"[scheduler] sync_results done: {updated} updated.")
    except Exception as e:
        logger.error(f"[scheduler] sync_results failed: {e}", exc_info=True)
        await _log_job("sync_results", "error", 0, str(e))


async def job_retrain_model() -> None:
    logger.info("[scheduler] retrain_model starting...")
    try:
        from app.ml.trainer import ModelTrainer
        from app.services.prediction_service import PredictionService
        trainer = ModelTrainer()
        version = await trainer.train()
        refreshed = 0
        if version:
            ps = PredictionService()
            refreshed = await ps.generate_upcoming_predictions(force_refresh=True, stale_only=True)

        await _log_job(
            "retrain_model",
            "success",
            refreshed if version else 0,
            None if version else "insufficient_data",
        )
        logger.info(f"[scheduler] retrain_model done: {version}")
    except Exception as e:
        logger.error(f"[scheduler] retrain_model failed: {e}", exc_info=True)
        await _log_job("retrain_model", "error", 0, str(e))


async def job_generate_predictions() -> None:
    logger.info("[scheduler] generate_predictions starting...")
    try:
        from app.services.prediction_service import PredictionService
        service = PredictionService()
        count = await service.generate_upcoming_predictions()
        await _log_job("generate_predictions", "success", count)
        logger.info(f"[scheduler] generate_predictions done: {count} predictions.")
    except Exception as e:
        logger.error(f"[scheduler] generate_predictions failed: {e}", exc_info=True)
        await _log_job("generate_predictions", "error", 0, str(e))


async def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    # sync_fixtures at 06:00 and 18:00 UTC
    scheduler.add_job(job_sync_fixtures, CronTrigger(hour="6,18", minute=0), id="sync_fixtures")

    # sync_results every 2 hours
    scheduler.add_job(job_sync_results, IntervalTrigger(hours=2), id="sync_results")

    # retrain_model every Monday at 03:00 UTC
    scheduler.add_job(job_retrain_model, CronTrigger(day_of_week="mon", hour=3, minute=0), id="retrain_model")

    # generate_predictions daily at 07:00 UTC
    scheduler.add_job(job_generate_predictions, CronTrigger(hour=7, minute=0), id="generate_predictions")

    scheduler.start()
    logger.info("APScheduler started with 4 jobs.")
    return scheduler
