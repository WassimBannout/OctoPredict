"""
29-feature engineering for OctoPredict.

All queries use WHERE utc_date < :match_date to prevent data leakage.

Feature categories:
1. Elo (5): elo_home, elo_away, elo_diff, elo_home_momentum, elo_away_momentum
2. Rolling form last 5 (10): home/away_form_pts, home/away_form_gf, home/away_form_ga,
                              home/away_form_gd, home/away_wins_last5
3. Clean sheets (2): home/away_clean_sheets_last5
4. Head-to-head last 5 (4): h2h_home_wins, h2h_draws, h2h_away_wins, h2h_goal_diff
5. League position (4): home/away_league_pos, position_diff, points_diff
6. Context (4): days_since_home_last_match, days_since_away_last_match,
                home_home_form_pts, away_away_form_pts
"""
from __future__ import annotations

from datetime import datetime
from typing import NamedTuple
from collections import defaultdict

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match, MatchStatus, MatchOutcome
from app.models.elo_rating import EloRating
from app.utils.logging import get_logger

logger = get_logger(__name__)

FEATURE_NAMES = [
    # Elo (5)
    "elo_home", "elo_away", "elo_diff", "elo_home_momentum", "elo_away_momentum",
    # Home form (5)
    "home_form_pts", "home_form_gf", "home_form_ga", "home_form_gd", "home_wins_last5",
    # Away form (5)
    "away_form_pts", "away_form_gf", "away_form_ga", "away_form_gd", "away_wins_last5",
    # Clean sheets (2)
    "home_clean_sheets_last5", "away_clean_sheets_last5",
    # H2H (4)
    "h2h_home_wins", "h2h_draws", "h2h_away_wins", "h2h_goal_diff",
    # League position (4)
    "home_league_pos", "away_league_pos", "position_diff", "points_diff",
    # Context (4)
    "days_since_home_last_match", "days_since_away_last_match",
    "home_home_form_pts", "away_away_form_pts",
]

INITIAL_ELO = 1500.0
_LEAGUE_PROGRESS_CACHE: dict[tuple[str, str], dict] = {}


class FeatureVector(NamedTuple):
    features: list[float]
    feature_dict: dict[str, float]
    h2h_available: bool


async def _get_elo(session: AsyncSession, team_id: int, before: datetime) -> float:
    stmt = (
        select(EloRating.rating)
        .where(EloRating.team_id == team_id)
        .where(EloRating.recorded_at < before)
        .order_by(EloRating.recorded_at.desc())
        .limit(1)
    )
    result = await session.scalar(stmt)
    return float(result) if result is not None else INITIAL_ELO


async def _get_elo_momentum(
    session: AsyncSession,
    team_id: int,
    before: datetime,
    n: int = 5,
) -> float:
    """Sum of Elo rating changes over last N matches. Positive = improving, negative = declining."""
    stmt = (
        select(EloRating.rating_change)
        .where(EloRating.team_id == team_id)
        .where(EloRating.recorded_at < before)
        .order_by(EloRating.recorded_at.desc())
        .limit(n)
    )
    rows = list(await session.scalars(stmt))
    return float(sum(rows)) if rows else 0.0


async def _get_recent_matches(
    session: AsyncSession,
    team_id: int,
    before: datetime,
    n: int = 5,
    venue: str | None = None,  # "home" | "away" | None
) -> list[Match]:
    if venue == "home":
        condition = and_(
            Match.home_team_id == team_id,
            Match.status == MatchStatus.FINISHED,
            Match.utc_date < before,
        )
    elif venue == "away":
        condition = and_(
            Match.away_team_id == team_id,
            Match.status == MatchStatus.FINISHED,
            Match.utc_date < before,
        )
    else:
        condition = and_(
            or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
            Match.status == MatchStatus.FINISHED,
            Match.utc_date < before,
        )
    stmt = (
        select(Match)
        .where(condition)
        .order_by(Match.utc_date.desc())
        .limit(n)
    )
    return list(await session.scalars(stmt))


def _form_stats(matches: list[Match], team_id: int) -> tuple[float, float, float, float, float]:
    """Returns (pts, gf, ga, wins, clean_sheets) for a team over a list of matches."""
    pts = gf = ga = wins = clean_sheets = 0.0
    for m in matches:
        is_home = m.home_team_id == team_id
        if is_home:
            gs = m.home_score or 0
            gc = m.away_score or 0
        else:
            gs = m.away_score or 0
            gc = m.home_score or 0

        gf += gs
        ga += gc
        if gc == 0:
            clean_sheets += 1

        if m.outcome == MatchOutcome.HOME_WIN:
            if is_home:
                pts += 3
                wins += 1
            # else loss → 0
        elif m.outcome == MatchOutcome.AWAY_WIN:
            if not is_home:
                pts += 3
                wins += 1
        elif m.outcome == MatchOutcome.DRAW:
            pts += 1

    return pts, gf, ga, wins, clean_sheets


async def _get_h2h(
    session: AsyncSession,
    home_team_id: int,
    away_team_id: int,
    before: datetime,
    n: int = 5,
) -> tuple[float, float, float, float]:
    """Returns (h2h_home_wins, h2h_draws, h2h_away_wins, h2h_goal_diff) in last n H2H meetings.

    h2h_goal_diff is the average goal difference from home_team_id's perspective.
    """
    stmt = (
        select(Match)
        .where(
            or_(
                and_(Match.home_team_id == home_team_id, Match.away_team_id == away_team_id),
                and_(Match.home_team_id == away_team_id, Match.away_team_id == home_team_id),
            )
        )
        .where(Match.status == MatchStatus.FINISHED)
        .where(Match.utc_date < before)
        .order_by(Match.utc_date.desc())
        .limit(n)
    )
    matches = list(await session.scalars(stmt))
    hw = draws = aw = 0
    total_gd = 0.0
    for m in matches:
        if m.home_team_id == home_team_id:
            gd = (m.home_score or 0) - (m.away_score or 0)
        else:
            gd = (m.away_score or 0) - (m.home_score or 0)
        total_gd += gd

        if m.outcome == MatchOutcome.HOME_WIN:
            if m.home_team_id == home_team_id:
                hw += 1
            else:
                aw += 1
        elif m.outcome == MatchOutcome.AWAY_WIN:
            if m.away_team_id == away_team_id:
                aw += 1
            else:
                hw += 1
        elif m.outcome == MatchOutcome.DRAW:
            draws += 1

    h2h_goal_diff = total_gd / len(matches) if matches else 0.0
    return float(hw), float(draws), float(aw), h2h_goal_diff


async def _get_league_snapshot(
    session: AsyncSession,
    competition_code: str,
    season: str,
    before: datetime,
) -> tuple[dict[int, int], dict[int, int]]:
    """
    Build league table snapshot before match kickoff.
    Returns (positions_by_team_id, points_by_team_id).
    """
    key = (competition_code, season)
    state = _LEAGUE_PROGRESS_CACHE.get(key)
    if state is None:
        stmt = (
            select(Match)
            .where(Match.competition_code == competition_code)
            .where(Match.season == season)
            .where(Match.status == MatchStatus.FINISHED)
            .where(Match.outcome.isnot(None))
            .order_by(Match.utc_date)
        )
        all_matches = list(await session.scalars(stmt))
        state = {
            "all_matches": all_matches,
            "idx": 0,
            "last_before": datetime.min,
            "table": defaultdict(lambda: {"points": 0, "gd": 0, "gf": 0}),
        }
        _LEAGUE_PROGRESS_CACHE[key] = state

    # If caller asks for an older timestamp, rebuild state from scratch.
    if before < state["last_before"]:
        state["idx"] = 0
        state["last_before"] = datetime.min
        state["table"] = defaultdict(lambda: {"points": 0, "gd": 0, "gf": 0})

    all_matches: list[Match] = state["all_matches"]
    idx: int = state["idx"]
    table: dict[int, dict[str, int]] = state["table"]

    while idx < len(all_matches) and all_matches[idx].utc_date < before:
        m = all_matches[idx]
        h_id = m.home_team_id
        a_id = m.away_team_id
        hs = int(m.home_score or 0)
        a_s = int(m.away_score or 0)

        table[h_id]["gf"] += hs
        table[h_id]["gd"] += hs - a_s
        table[a_id]["gf"] += a_s
        table[a_id]["gd"] += a_s - hs

        if m.outcome == MatchOutcome.HOME_WIN:
            table[h_id]["points"] += 3
        elif m.outcome == MatchOutcome.AWAY_WIN:
            table[a_id]["points"] += 3
        elif m.outcome == MatchOutcome.DRAW:
            table[h_id]["points"] += 1
            table[a_id]["points"] += 1
        idx += 1

    state["idx"] = idx
    state["last_before"] = before

    sorted_rows = sorted(
        table.items(),
        key=lambda item: (
            -item[1]["points"],
            -item[1]["gd"],
            -item[1]["gf"],
            item[0],
        ),
    )
    positions = {team_id: idx + 1 for idx, (team_id, _) in enumerate(sorted_rows)}
    points = {team_id: stats["points"] for team_id, stats in table.items()}
    return positions, points


async def build_features(
    session: AsyncSession,
    match: Match,
) -> FeatureVector:
    """Build 29-feature vector for a match. No data leakage."""
    ref_date = match.utc_date

    home_id = match.home_team_id
    away_id = match.away_team_id

    # ── Elo ──
    elo_home = await _get_elo(session, home_id, ref_date)
    elo_away = await _get_elo(session, away_id, ref_date)
    elo_diff = elo_home - elo_away
    elo_home_momentum = await _get_elo_momentum(session, home_id, ref_date)
    elo_away_momentum = await _get_elo_momentum(session, away_id, ref_date)

    # ── Rolling form last 5 ──
    home_recent = await _get_recent_matches(session, home_id, ref_date)
    away_recent = await _get_recent_matches(session, away_id, ref_date)
    home_form_pts, home_form_gf, home_form_ga, home_wins_last5, home_clean_sheets = _form_stats(home_recent, home_id)
    away_form_pts, away_form_gf, away_form_ga, away_wins_last5, away_clean_sheets = _form_stats(away_recent, away_id)
    home_form_gd = home_form_gf - home_form_ga
    away_form_gd = away_form_gf - away_form_ga

    # ── H2H ──
    h2h_home_wins, h2h_draws, h2h_away_wins, h2h_goal_diff = await _get_h2h(session, home_id, away_id, ref_date)
    h2h_available = (h2h_home_wins + h2h_draws + h2h_away_wins) > 0

    # ── League position ──
    table_positions: dict[int, int] = {}
    table_points: dict[int, int] = {}
    if (
        match.home_position is None
        or match.away_position is None
        or match.home_points is None
        or match.away_points is None
    ):
        table_positions, table_points = await _get_league_snapshot(
            session,
            match.competition_code,
            match.season,
            ref_date,
        )

    default_pos = max(1, (len(table_positions) + 1) // 2) if table_positions else 10
    home_league_pos = float(
        match.home_position if match.home_position is not None else table_positions.get(home_id, default_pos)
    )
    away_league_pos = float(
        match.away_position if match.away_position is not None else table_positions.get(away_id, default_pos)
    )
    position_diff = home_league_pos - away_league_pos
    home_pts = float(match.home_points if match.home_points is not None else table_points.get(home_id, 0))
    away_pts = float(match.away_points if match.away_points is not None else table_points.get(away_id, 0))
    points_diff = home_pts - away_pts

    # ── Context ──
    home_last = await _get_recent_matches(session, home_id, ref_date, n=1)
    away_last = await _get_recent_matches(session, away_id, ref_date, n=1)
    days_since_home = (
        (ref_date - home_last[0].utc_date).days if home_last else 7
    )
    days_since_away = (
        (ref_date - away_last[0].utc_date).days if away_last else 7
    )

    home_home_recent = await _get_recent_matches(session, home_id, ref_date, n=5, venue="home")
    away_away_recent = await _get_recent_matches(session, away_id, ref_date, n=5, venue="away")
    home_home_form_pts, *_ = _form_stats(home_home_recent, home_id)
    away_away_form_pts, *_ = _form_stats(away_away_recent, away_id)

    feature_dict = {
        "elo_home": elo_home,
        "elo_away": elo_away,
        "elo_diff": elo_diff,
        "elo_home_momentum": elo_home_momentum,
        "elo_away_momentum": elo_away_momentum,
        "home_form_pts": home_form_pts,
        "home_form_gf": home_form_gf,
        "home_form_ga": home_form_ga,
        "home_form_gd": home_form_gd,
        "home_wins_last5": home_wins_last5,
        "away_form_pts": away_form_pts,
        "away_form_gf": away_form_gf,
        "away_form_ga": away_form_ga,
        "away_form_gd": away_form_gd,
        "away_wins_last5": away_wins_last5,
        "home_clean_sheets_last5": home_clean_sheets,
        "away_clean_sheets_last5": away_clean_sheets,
        "h2h_home_wins": h2h_home_wins,
        "h2h_draws": h2h_draws,
        "h2h_away_wins": h2h_away_wins,
        "h2h_goal_diff": h2h_goal_diff,
        "home_league_pos": home_league_pos,
        "away_league_pos": away_league_pos,
        "position_diff": position_diff,
        "points_diff": points_diff,
        "days_since_home_last_match": float(days_since_home),
        "days_since_away_last_match": float(days_since_away),
        "home_home_form_pts": home_home_form_pts,
        "away_away_form_pts": away_away_form_pts,
    }

    features = [feature_dict[name] for name in FEATURE_NAMES]
    return FeatureVector(features=features, feature_dict=feature_dict, h2h_available=h2h_available)
