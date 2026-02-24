from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.team import Team
from app.models.match import Match, MatchStatus
from app.config import get_settings
from app.services.football_api import FootballDataClient

router = APIRouter(tags=["leagues"])
settings = get_settings()

LEAGUE_DISPLAY = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
}


@router.get("/leagues")
async def list_leagues(db: Annotated[AsyncSession, Depends(get_db)]):
    result = []
    for code in settings.leagues:
        team_count = await db.scalar(
            select(func.count()).select_from(Team).where(Team.competition_code == code)
        )
        match_count = await db.scalar(
            select(func.count()).select_from(Match).where(Match.competition_code == code)
        )
        result.append({
            "code": code,
            "name": LEAGUE_DISPLAY.get(code, code),
            "team_count": team_count or 0,
            "match_count": match_count or 0,
        })
    return result


@router.get("/leagues/{code}/standings")
async def get_standings(code: str):
    """Fetch live standings from football-data.org."""
    if code not in settings.leagues:
        raise HTTPException(status_code=404, detail=f"League {code} not tracked")
    client = FootballDataClient()
    try:
        data = await client.get_standings(code)
        await client.close()
        standings = data.get("standings", [])
        # Return only the total standings table
        for s in standings:
            if s.get("type") == "TOTAL":
                return {"league_code": code, "standings": s.get("table", [])}
        return {"league_code": code, "standings": standings}
    except Exception as e:
        await client.close()
        raise HTTPException(status_code=503, detail=f"Could not fetch standings: {e}")
