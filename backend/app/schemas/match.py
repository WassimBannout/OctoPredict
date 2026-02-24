from datetime import datetime
from pydantic import BaseModel
from app.models.match import MatchStatus, MatchOutcome


class TeamSummary(BaseModel):
    id: int
    name: str
    short_name: str
    tla: str
    crest_url: str | None

    model_config = {"from_attributes": True}


class PredictionSummary(BaseModel):
    prob_home_win: float
    prob_draw: float
    prob_away_win: float
    predicted_outcome: str
    confidence: str
    model_version: str

    model_config = {"from_attributes": True}


class MatchResponse(BaseModel):
    id: int
    external_id: int
    competition_code: str
    season: str
    matchday: int | None
    utc_date: datetime
    status: MatchStatus
    home_team: TeamSummary
    away_team: TeamSummary
    home_score: int | None
    away_score: int | None
    outcome: MatchOutcome | None
    home_position: int | None
    away_position: int | None
    prediction: PredictionSummary | None = None
    home_elo: float | None = None
    away_elo: float | None = None

    model_config = {"from_attributes": True}


class MatchDetail(MatchResponse):
    features: dict | None = None
