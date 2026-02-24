from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.schemas.match import MatchResponse, MatchDetail
from app.services.elo_service import EloService
from app.ml.features import build_features

router = APIRouter(tags=["matches"])
_elo_service = EloService()


async def _enrich_match(match: Match, session: AsyncSession, elo_ratings: dict) -> dict:
    data = {
        "id": match.id,
        "external_id": match.external_id,
        "competition_code": match.competition_code,
        "season": match.season,
        "matchday": match.matchday,
        "utc_date": match.utc_date,
        "status": match.status,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "home_score": match.home_score,
        "away_score": match.away_score,
        "outcome": match.outcome,
        "home_position": match.home_position,
        "away_position": match.away_position,
        "prediction": match.prediction,
        "home_elo": elo_ratings.get(match.home_team_id),
        "away_elo": elo_ratings.get(match.away_team_id),
    }
    return data


@router.get("/matches/upcoming", response_model=list[MatchResponse])
async def get_upcoming_matches(
    db: Annotated[AsyncSession, Depends(get_db)],
    league_code: str | None = None,
    days_ahead: int = Query(default=7, ge=1, le=30),
):
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days_ahead)
    stmt = (
        select(Match)
        .where(Match.status.in_([MatchStatus.SCHEDULED, MatchStatus.TIMED]))
        .where(Match.utc_date >= now)
        .where(Match.utc_date <= cutoff)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.prediction),
        )
        .order_by(Match.utc_date)
    )
    if league_code:
        stmt = stmt.where(Match.competition_code == league_code)

    matches = list(await db.scalars(stmt))
    elo_ratings = await _elo_service.get_current_ratings(db)
    result = []
    for m in matches:
        d = await _enrich_match(m, db, elo_ratings)
        result.append(MatchResponse(**d))
    return result


@router.get("/matches/recent", response_model=list[MatchResponse])
async def get_recent_matches(
    db: Annotated[AsyncSession, Depends(get_db)],
    league_code: str | None = None,
    days_back: int = Query(default=7, ge=1, le=30),
):
    now = datetime.utcnow()
    since = now - timedelta(days=days_back)
    stmt = (
        select(Match)
        .where(Match.status == MatchStatus.FINISHED)
        .where(Match.utc_date >= since)
        .where(Match.utc_date <= now)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.prediction),
        )
        .order_by(Match.utc_date.desc())
    )
    if league_code:
        stmt = stmt.where(Match.competition_code == league_code)

    matches = list(await db.scalars(stmt))
    elo_ratings = await _elo_service.get_current_ratings(db)
    result = []
    for m in matches:
        d = await _enrich_match(m, db, elo_ratings)
        result.append(MatchResponse(**d))
    return result


@router.get("/matches/{match_id}", response_model=MatchResponse)
async def get_match(
    match_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = (
        select(Match)
        .where(Match.id == match_id)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.prediction),
        )
    )
    match = await db.scalar(stmt)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    elo_ratings = await _elo_service.get_current_ratings(db)
    d = await _enrich_match(match, db, elo_ratings)
    return MatchResponse(**d)


@router.get("/matches/{match_id}/features")
async def get_match_features(
    match_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Transparency endpoint: returns the feature vector for a match."""
    match = await db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    try:
        fv = await build_features(db, match)
        return {"match_id": match_id, "features": fv.feature_dict, "h2h_available": fv.h2h_available}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
