from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.team import Team
from app.models.match import Match, MatchStatus, MatchOutcome
from app.models.job_log import JobLog
from app.services.football_api import FootballDataClient
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

LEAGUE_NAMES = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
}


def _parse_utc_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)  # store as naive UTC
    except Exception:
        return None


def _determine_outcome(home_score: int | None, away_score: int | None) -> MatchOutcome | None:
    if home_score is None or away_score is None:
        return None
    if home_score > away_score:
        return MatchOutcome.HOME_WIN
    elif home_score < away_score:
        return MatchOutcome.AWAY_WIN
    else:
        return MatchOutcome.DRAW


class DataSyncService:
    def __init__(self) -> None:
        self.api = FootballDataClient()

    async def _upsert_team(self, session: AsyncSession, team_data: dict, competition_code: str) -> Team:
        external_id = team_data["id"]
        stmt = select(Team).where(Team.external_id == external_id)
        team = await session.scalar(stmt)
        if team is None:
            team = Team(
                external_id=external_id,
                name=team_data.get("name", ""),
                short_name=team_data.get("shortName", team_data.get("name", "")),
                tla=team_data.get("tla", "???"),
                crest_url=team_data.get("crest"),
                competition_code=competition_code,
            )
            session.add(team)
        else:
            team.name = team_data.get("name", team.name)
            team.short_name = team_data.get("shortName", team.short_name)
            team.tla = team_data.get("tla", team.tla)
            team.crest_url = team_data.get("crest", team.crest_url)
        return team

    async def _upsert_match(
        self,
        session: AsyncSession,
        match_data: dict,
        competition_code: str,
        season_str: str,
        home_team: Team,
        away_team: Team,
    ) -> tuple[Match, bool]:
        external_id = match_data["id"]
        stmt = select(Match).where(Match.external_id == external_id)
        match = await session.scalar(stmt)
        is_new = match is None

        utc_date = _parse_utc_date(match_data.get("utcDate"))
        if utc_date is None:
            utc_date = datetime.utcnow()

        status_raw = match_data.get("status", "SCHEDULED")
        try:
            status = MatchStatus(status_raw)
        except ValueError:
            status = MatchStatus.SCHEDULED

        score = match_data.get("score", {})
        full_time = score.get("fullTime", {}) or {}
        home_score = full_time.get("home")
        away_score = full_time.get("away")
        outcome = _determine_outcome(home_score, away_score) if status == MatchStatus.FINISHED else None

        if match is None:
            match = Match(
                external_id=external_id,
                competition_code=competition_code,
                season=season_str,
                matchday=match_data.get("matchday"),
                utc_date=utc_date,
                status=status,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_score=home_score,
                away_score=away_score,
                outcome=outcome,
            )
            session.add(match)
        else:
            match.status = status
            match.utc_date = utc_date
            match.matchday = match_data.get("matchday", match.matchday)
            if status == MatchStatus.FINISHED:
                match.home_score = home_score
                match.away_score = away_score
                match.outcome = outcome

        return match, is_new

    async def sync_competition(self, competition_code: str, season: int) -> int:
        """Sync all teams and matches for a given competition and season."""
        logger.info(f"Syncing {competition_code} season {season}...")
        season_str = str(season)
        count = 0

        async with AsyncSessionLocal() as session:
            try:
                # Fetch and upsert teams
                teams_data = await self.api.get_teams(competition_code, season)
                team_map: dict[int, Team] = {}
                for t in teams_data.get("teams", []):
                    team = await self._upsert_team(session, t, competition_code)
                    await session.flush()
                    team_map[t["id"]] = team

                # Fetch and upsert matches
                matches_data = await self.api.get_matches(competition_code, season=season)
                for m in matches_data.get("matches", []):
                    home_ext = m.get("homeTeam", {}).get("id")
                    away_ext = m.get("awayTeam", {}).get("id")
                    if home_ext not in team_map or away_ext not in team_map:
                        continue
                    await self._upsert_match(
                        session, m, competition_code, season_str,
                        team_map[home_ext], team_map[away_ext]
                    )
                    count += 1

                await session.commit()
                logger.info(f"  {competition_code} {season}: {count} matches synced.")
            except Exception as e:
                await session.rollback()
                logger.error(f"  Error syncing {competition_code} {season}: {e}", exc_info=True)

        return count

    async def seed_historical_data(self) -> None:
        """Fetch last N seasons for all configured leagues."""
        current_year = datetime.utcnow().year
        total = 0
        for league in settings.leagues:
            for offset in range(settings.seasons_to_fetch):
                season = current_year - 1 - offset
                try:
                    count = await self.sync_competition(league, season)
                    total += count
                except Exception as e:
                    logger.error(f"Failed {league} {season}: {e}")
        logger.info(f"Historical seed complete: {total} matches total.")

    async def sync_upcoming_fixtures(self) -> int:
        """Sync upcoming fixtures for all leagues (next ~2 weeks)."""
        from datetime import timedelta
        date_from = datetime.utcnow().strftime("%Y-%m-%d")
        date_to = (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%d")
        count = 0
        async with AsyncSessionLocal() as session:
            for league in settings.leagues:
                try:
                    data = await self.api.get_matches(
                        league, date_from=date_from, date_to=date_to
                    )
                    teams_cache: dict[int, Team] = {}
                    for m in data.get("matches", []):
                        home_ext = m.get("homeTeam", {}).get("id")
                        away_ext = m.get("awayTeam", {}).get("id")
                        # Ensure teams exist
                        for ext_id, t_data in [
                            (home_ext, m.get("homeTeam", {})),
                            (away_ext, m.get("awayTeam", {})),
                        ]:
                            if ext_id not in teams_cache:
                                team = await self._upsert_team(session, t_data, league)
                                await session.flush()
                                teams_cache[ext_id] = team
                        if home_ext not in teams_cache or away_ext not in teams_cache:
                            continue
                        season_str = str(m.get("season", {}).get("startDate", "")[:4] or datetime.utcnow().year)
                        await self._upsert_match(
                            session, m, league, season_str,
                            teams_cache[home_ext], teams_cache[away_ext]
                        )
                        count += 1
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    logger.error(f"sync_upcoming {league}: {e}")
        return count

    async def sync_recent_results(self) -> int:
        """Update scores for recently finished matches."""
        from datetime import timedelta
        date_from = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
        date_to = datetime.utcnow().strftime("%Y-%m-%d")
        updated = 0
        async with AsyncSessionLocal() as session:
            for league in settings.leagues:
                try:
                    data = await self.api.get_matches(
                        league, date_from=date_from, date_to=date_to, status="FINISHED"
                    )
                    for m in data.get("matches", []):
                        stmt = select(Match).where(Match.external_id == m["id"])
                        match = await session.scalar(stmt)
                        if match is None:
                            continue
                        score = m.get("score", {}).get("fullTime", {}) or {}
                        match.home_score = score.get("home")
                        match.away_score = score.get("away")
                        match.status = MatchStatus.FINISHED
                        match.outcome = _determine_outcome(match.home_score, match.away_score)
                        updated += 1
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    logger.error(f"sync_results {league}: {e}")
        return updated

    async def _log_job(self, session: AsyncSession, name: str, status: str, count: int, error: str | None = None) -> None:
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
