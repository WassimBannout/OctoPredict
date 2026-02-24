from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.job_log import JobLog
from app.schemas.stats import ModelStats, OverviewStats
from app.ml.model_store import ModelStore
from app.ml.features import FEATURE_NAMES
from app.config import get_settings
from app.services.prediction_service import PredictionService

router = APIRouter(tags=["stats"])
settings = get_settings()


@router.get("/stats/model", response_model=ModelStats)
async def get_model_stats():
    store = ModelStore()
    predictor, meta = store.load_latest()
    if predictor is None:
        # Keep frontend stable even before first successful training.
        return ModelStats(
            version="elo_fallback",
            model_type="elo_fallback",
            created_at=None,
            metrics={},
            feature_importances={},
            feature_names=list(FEATURE_NAMES),
        )

    importances = {}
    if hasattr(predictor, "feature_importances"):
        importances = predictor.feature_importances(list(FEATURE_NAMES))

    return ModelStats(
        version=meta.get("version", "unknown"),
        model_type=meta.get("model_type", "xgboost"),
        created_at=meta.get("created_at"),
        metrics=meta.get("metrics", {}),
        feature_importances=importances,
        feature_names=list(FEATURE_NAMES),
    )


@router.get("/stats/overview", response_model=OverviewStats)
async def get_overview(db: Annotated[AsyncSession, Depends(get_db)]):
    total_matches = await db.scalar(select(func.count()).select_from(Match)) or 0
    finished = await db.scalar(
        select(func.count()).select_from(Match).where(Match.status == MatchStatus.FINISHED)
    ) or 0
    upcoming = await db.scalar(
        select(func.count()).select_from(Match).where(
            Match.status.in_([MatchStatus.SCHEDULED, MatchStatus.TIMED])
        )
    ) or 0
    total_preds = await db.scalar(select(func.count()).select_from(Prediction)) or 0
    resolved_preds = await db.scalar(
        select(func.count()).select_from(Prediction).where(Prediction.actual_outcome.isnot(None))
    ) or 0
    correct_preds = await db.scalar(
        select(func.count()).select_from(Prediction).where(Prediction.is_correct == True)
    ) or 0

    accuracy = correct_preds / resolved_preds if resolved_preds > 0 else None

    # Last successful sync
    last_sync_log = await db.scalar(
        select(JobLog).where(JobLog.status == "success").order_by(JobLog.finished_at.desc()).limit(1)
    )
    last_sync = last_sync_log.finished_at.isoformat() if last_sync_log else None

    return OverviewStats(
        total_matches=total_matches,
        finished_matches=finished,
        upcoming_matches=upcoming,
        total_predictions=total_preds,
        resolved_predictions=resolved_preds,
        overall_accuracy=accuracy,
        leagues=settings.leagues,
        last_sync=last_sync,
    )


@router.post("/admin/sync")
async def manual_sync():
    """Manually trigger a full data refresh."""
    from app.services.data_sync import DataSyncService
    from app.services.elo_service import EloService
    sync = DataSyncService()
    elo = EloService()
    ps = PredictionService()
    count = await sync.sync_upcoming_fixtures()
    results = await sync.sync_recent_results()
    await elo.recompute_all()
    preds = await ps.generate_upcoming_predictions(force_refresh=True, stale_only=True)
    resolved = await ps.resolve_predictions()
    return {"synced": count, "results_updated": results, "predictions": preds, "resolved": resolved}
