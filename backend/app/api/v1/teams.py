from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.team import Team
from app.models.match import Match, MatchStatus, MatchOutcome
from app.schemas.team import TeamResponse, TeamDetail
from app.services.elo_service import EloService
from app.services.elo_service import INITIAL_RATING as INITIAL_ELO

router = APIRouter(tags=["teams"])
_elo_service = EloService()


@router.get("/teams", response_model=list[TeamResponse])
async def list_teams(
    db: Annotated[AsyncSession, Depends(get_db)],
    league_code: str | None = None,
):
    stmt = select(Team)
    if league_code:
        stmt = stmt.where(Team.competition_code == league_code)
    stmt = stmt.order_by(Team.name)
    teams = list(await db.scalars(stmt))
    elo_ratings = await _elo_service.get_current_ratings(db)
    return [
        TeamResponse(
            id=t.id, external_id=t.external_id, name=t.name, short_name=t.short_name,
            tla=t.tla, crest_url=t.crest_url, competition_code=t.competition_code,
            current_elo=elo_ratings.get(t.id, INITIAL_ELO),
        )
        for t in teams
    ]


@router.get("/teams/{team_id}", response_model=TeamDetail)
async def get_team(
    team_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    team = await db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    elo_ratings = await _elo_service.get_current_ratings(db)
    elo_history = await _elo_service.get_team_elo_history(team_id)

    # Last 5 matches
    from sqlalchemy import or_, and_
    stmt = (
        select(Match)
        .where(
            or_(Match.home_team_id == team_id, Match.away_team_id == team_id)
        )
        .where(Match.status == MatchStatus.FINISHED)
        .order_by(Match.utc_date.desc())
        .limit(5)
    )
    recent_matches = list(await db.scalars(stmt))

    # Home/away record
    home_wins = home_draws = home_losses = 0
    away_wins = away_draws = away_losses = 0
    last_5 = []
    for m in recent_matches:
        is_home = m.home_team_id == team_id
        result_str = "?"
        if m.outcome == MatchOutcome.HOME_WIN:
            if is_home:
                home_wins += 1
                result_str = "W"
            else:
                away_losses += 1
                result_str = "L"
        elif m.outcome == MatchOutcome.AWAY_WIN:
            if not is_home:
                away_wins += 1
                result_str = "W"
            else:
                home_losses += 1
                result_str = "L"
        elif m.outcome == MatchOutcome.DRAW:
            if is_home:
                home_draws += 1
            else:
                away_draws += 1
            result_str = "D"
        last_5.append({"match_id": m.id, "date": m.utc_date.isoformat(), "result": result_str})

    return TeamDetail(
        id=team.id, external_id=team.external_id, name=team.name,
        short_name=team.short_name, tla=team.tla, crest_url=team.crest_url,
        competition_code=team.competition_code,
        current_elo=elo_ratings.get(team.id, INITIAL_ELO),
        elo_history=elo_history,
        home_record={"wins": home_wins, "draws": home_draws, "losses": home_losses},
        away_record={"wins": away_wins, "draws": away_draws, "losses": away_losses},
        last_5_matches=last_5,
    )
