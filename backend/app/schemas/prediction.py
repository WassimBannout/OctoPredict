from datetime import datetime
from pydantic import BaseModel
from app.schemas.match import MatchResponse


class PredictionResponse(BaseModel):
    id: int
    match_id: int
    prob_home_win: float
    prob_draw: float
    prob_away_win: float
    predicted_outcome: str
    confidence: str
    features_snapshot: dict | None
    actual_outcome: str | None
    is_correct: bool | None
    brier_score: float | None
    rps_score: float | None
    model_version: str
    predicted_at: datetime
    match: MatchResponse | None = None

    model_config = {"from_attributes": True}


class PredictionHistory(BaseModel):
    items: list[PredictionResponse]
    total: int
    page: int
    limit: int


class AccuracyStats(BaseModel):
    total_predictions: int
    resolved_predictions: int
    correct_predictions: int
    accuracy: float
    display_accuracy: float | None
    accuracy_source: str
    avg_brier_score: float | None
    avg_rps_score: float | None
    validation_accuracy: float | None
    validation_brier_score: float | None
    validation_rps_score: float | None
    validation_samples: int | None
    league_code: str | None
    window_days: int
