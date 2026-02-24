from pydantic import BaseModel


class ModelStats(BaseModel):
    version: str
    model_type: str
    created_at: str | None
    metrics: dict
    feature_importances: dict[str, float]
    feature_names: list[str]


class OverviewStats(BaseModel):
    total_matches: int
    finished_matches: int
    upcoming_matches: int
    total_predictions: int
    resolved_predictions: int
    overall_accuracy: float | None
    leagues: list[str]
    last_sync: str | None
