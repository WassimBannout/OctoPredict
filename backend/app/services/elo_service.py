import math
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.match import Match, MatchStatus, MatchOutcome
from app.models.elo_rating import EloRating
from app.models.team import Team
from app.utils.logging import get_logger

logger = get_logger(__name__)

INITIAL_RATING = 1500.0
K_FACTOR = 32.0
HOME_ADVANTAGE = 100.0  # Elo points added to home team's rating for expected score


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def goal_margin_multiplier(
    home_score: int | None,
    away_score: int | None,
    outcome: MatchOutcome,
) -> float:
    """Scale K by log-based margin. Caps at 2.5. Falls back to 1.0 if scores unknown."""
    if home_score is None or away_score is None:
        return 1.0
    if outcome == MatchOutcome.DRAW:
        return 1.0
    goal_diff = abs(home_score - away_score)
    if goal_diff <= 0:
        return 1.0
    return min(2.5, 1.0 + math.log(goal_diff))


def update_elo(
    home_rating: float,
    away_rating: float,
    outcome: MatchOutcome,
    home_score: int | None = None,
    away_score: int | None = None,
) -> tuple[float, float, float, float]:
    """Return (new_home, new_away, home_change, away_change)."""
    # Apply home advantage only for expected score calculation
    home_eff = home_rating + HOME_ADVANTAGE
    exp_home = expected_score(home_eff, away_rating)
    exp_away = 1.0 - exp_home

    if outcome == MatchOutcome.HOME_WIN:
        actual_home, actual_away = 1.0, 0.0
    elif outcome == MatchOutcome.DRAW:
        actual_home, actual_away = 0.5, 0.5
    else:  # AWAY_WIN
        actual_home, actual_away = 0.0, 1.0

    multiplier = goal_margin_multiplier(home_score, away_score, outcome)
    k = K_FACTOR * multiplier

    home_change = k * (actual_home - exp_home)
    away_change = k * (actual_away - exp_away)

    return home_rating + home_change, away_rating + away_change, home_change, away_change


class EloService:
    async def recompute_all(self) -> None:
        """Recompute all Elo ratings from scratch in chronological order."""
        logger.info("Recomputing all Elo ratings...")

        async with AsyncSessionLocal() as session:
            # Clear existing ratings
            await session.execute(delete(EloRating))
            await session.commit()

            # Load all finished matches in chronological order
            stmt = (
                select(Match)
                .where(Match.status == MatchStatus.FINISHED)
                .where(Match.outcome.isnot(None))
                .order_by(Match.utc_date)
            )
            matches = list(await session.scalars(stmt))

            ratings: dict[int, float] = {}  # team_id → current rating

            for match in matches:
                home_id = match.home_team_id
                away_id = match.away_team_id

                home_r = ratings.get(home_id, INITIAL_RATING)
                away_r = ratings.get(away_id, INITIAL_RATING)

                new_home, new_away, home_chg, away_chg = update_elo(
                    home_r, away_r, match.outcome, match.home_score, match.away_score
                )

                ratings[home_id] = new_home
                ratings[away_id] = new_away

                session.add(EloRating(
                    team_id=home_id,
                    match_id=match.id,
                    rating=new_home,
                    rating_change=home_chg,
                    recorded_at=match.utc_date,
                ))
                session.add(EloRating(
                    team_id=away_id,
                    match_id=match.id,
                    rating=new_away,
                    rating_change=away_chg,
                    recorded_at=match.utc_date,
                ))

            await session.commit()
            logger.info(f"Elo recompute done. {len(ratings)} teams rated, {len(matches)} matches processed.")

    async def get_current_ratings(self, session: AsyncSession) -> dict[int, float]:
        """Get the latest Elo rating for each team."""
        from sqlalchemy import func

        # Get the max recorded_at per team
        subq = (
            select(EloRating.team_id, func.max(EloRating.recorded_at).label("max_date"))
            .group_by(EloRating.team_id)
            .subquery()
        )
        stmt = select(EloRating).join(
            subq,
            (EloRating.team_id == subq.c.team_id) & (EloRating.recorded_at == subq.c.max_date),
        )
        rows = await session.scalars(stmt)
        return {r.team_id: r.rating for r in rows}

    async def get_team_elo_history(self, team_id: int) -> list[dict]:
        """Return list of {date, rating, rating_change} for a team."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(EloRating)
                .where(EloRating.team_id == team_id)
                .order_by(EloRating.recorded_at)
            )
            rows = await session.scalars(stmt)
            return [
                {"date": r.recorded_at.isoformat(), "rating": r.rating, "change": r.rating_change}
                for r in rows
            ]

    async def update_for_match(self, match: Match) -> None:
        """Update Elo after a single match result."""
        async with AsyncSessionLocal() as session:
            current = await self.get_current_ratings(session)
            home_r = current.get(match.home_team_id, INITIAL_RATING)
            away_r = current.get(match.away_team_id, INITIAL_RATING)
            new_home, new_away, home_chg, away_chg = update_elo(
                home_r, away_r, match.outcome, match.home_score, match.away_score
            )

            session.add(EloRating(
                team_id=match.home_team_id,
                match_id=match.id,
                rating=new_home,
                rating_change=home_chg,
                recorded_at=match.utc_date,
            ))
            session.add(EloRating(
                team_id=match.away_team_id,
                match_id=match.id,
                rating=new_away,
                rating_change=away_chg,
                recorded_at=match.utc_date,
            ))
            await session.commit()
