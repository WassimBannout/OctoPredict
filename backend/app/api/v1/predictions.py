from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models.prediction import Prediction
from app.models.match import Match, MatchStatus
from app.schemas.prediction import PredictionHistory, PredictionResponse, AccuracyStats
from app.services.prediction_service import PredictionService
from app.ml.model_store import ModelStore

router = APIRouter(tags=["predictions"])
_pred_service = PredictionService()


@router.get("/predictions/history", response_model=PredictionHistory)
async def get_prediction_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    league_code: str | None = None,
):
    offset = (page - 1) * limit
    stmt = (
        select(Prediction)
        .join(Match, Prediction.match_id == Match.id)
        .options(
            selectinload(Prediction.match).selectinload(Match.home_team),
            selectinload(Prediction.match).selectinload(Match.away_team),
        )
        .order_by(Match.utc_date.desc())
        .offset(offset)
        .limit(limit)
    )
    if league_code:
        stmt = stmt.where(Match.competition_code == league_code)

    preds = list(await db.scalars(stmt))
    total_stmt = select(func.count()).select_from(Prediction).join(Match, Prediction.match_id == Match.id)
    if league_code:
        total_stmt = total_stmt.where(Match.competition_code == league_code)
    total = await db.scalar(total_stmt) or 0

    items = []
    for p in preds:
        m = p.match
        match_data = None
        if m:
            match_data = {
                "id": m.id, "external_id": m.external_id,
                "competition_code": m.competition_code, "season": m.season,
                "matchday": m.matchday, "utc_date": m.utc_date, "status": m.status,
                "home_team": m.home_team, "away_team": m.away_team,
                "home_score": m.home_score, "away_score": m.away_score,
                "outcome": m.outcome, "home_position": m.home_position,
                "away_position": m.away_position, "prediction": None,
                "home_elo": None, "away_elo": None,
            }
        items.append(PredictionResponse(
            id=p.id, match_id=p.match_id,
            prob_home_win=p.prob_home_win, prob_draw=p.prob_draw, prob_away_win=p.prob_away_win,
            predicted_outcome=p.predicted_outcome, confidence=p.confidence,
            features_snapshot=p.features_snapshot,
            actual_outcome=p.actual_outcome, is_correct=p.is_correct,
            brier_score=p.brier_score, rps_score=p.rps_score,
            model_version=p.model_version, predicted_at=p.predicted_at,
            match=match_data,
        ))

    return PredictionHistory(items=items, total=total, page=page, limit=limit)


@router.get("/predictions/accuracy", response_model=AccuracyStats)
async def get_accuracy(
    db: Annotated[AsyncSession, Depends(get_db)],
    league_code: str | None = None,
    window_days: int = Query(default=90, ge=1, le=365),
):
    since = datetime.utcnow() - timedelta(days=window_days)
    stmt = (
        select(Prediction)
        .join(Match, Prediction.match_id == Match.id)
        .where(Match.utc_date >= since)
    )
    if league_code:
        stmt = stmt.where(Match.competition_code == league_code)

    preds = list(await db.scalars(stmt))
    resolved = [p for p in preds if p.actual_outcome is not None]
    correct = [p for p in resolved if p.is_correct]

    brier_scores = [p.brier_score for p in resolved if p.brier_score is not None]
    rps_scores = [p.rps_score for p in resolved if p.rps_score is not None]
    live_accuracy = len(correct) / len(resolved) if resolved else 0.0
    live_brier = sum(brier_scores) / len(brier_scores) if brier_scores else None
    live_rps = sum(rps_scores) / len(rps_scores) if rps_scores else None

    validation_accuracy = None
    validation_brier = None
    validation_rps = None
    validation_n = None
    display_accuracy = live_accuracy if resolved else None
    accuracy_source = "resolved_predictions" if resolved else "none"

    if not resolved:
        _, meta = ModelStore().load_latest()
        metrics = (meta or {}).get("metrics", {}) if meta is not None else {}
        validation_accuracy = metrics.get("accuracy")
        validation_brier = metrics.get("brier")
        validation_rps = metrics.get("rps")
        validation_n = metrics.get("n")

        if validation_accuracy is not None:
            display_accuracy = float(validation_accuracy)
            accuracy_source = "model_validation"

    return AccuracyStats(
        total_predictions=len(preds),
        resolved_predictions=len(resolved),
        correct_predictions=len(correct),
        accuracy=live_accuracy,
        display_accuracy=display_accuracy,
        accuracy_source=accuracy_source,
        avg_brier_score=live_brier,
        avg_rps_score=live_rps,
        validation_accuracy=validation_accuracy,
        validation_brier_score=validation_brier,
        validation_rps_score=validation_rps,
        validation_samples=validation_n,
        league_code=league_code,
        window_days=window_days,
    )


@router.post("/predictions/generate")
async def generate_predictions(force_refresh: bool = Query(default=False)):
    """Manually trigger prediction generation/refresh for upcoming matches."""
    service = PredictionService()
    count = await service.generate_upcoming_predictions(
        force_refresh=force_refresh,
        stale_only=True,
    )
    return {"generated": count, "force_refresh": force_refresh}
