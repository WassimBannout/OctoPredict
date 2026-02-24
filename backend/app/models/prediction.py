from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.match import MatchOutcome


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), unique=True, index=True)

    prob_home_win: Mapped[float] = mapped_column(Float)
    prob_draw: Mapped[float] = mapped_column(Float)
    prob_away_win: Mapped[float] = mapped_column(Float)
    predicted_outcome: Mapped[MatchOutcome] = mapped_column(String(20))
    confidence: Mapped[str] = mapped_column(String(10))  # LOW / MEDIUM / HIGH

    features_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    actual_outcome: Mapped[MatchOutcome | None] = mapped_column(String(20), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    brier_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rps_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    model_version: Mapped[str] = mapped_column(String(50), default="elo_fallback")
    predicted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    match: Mapped["Match"] = relationship("Match", back_populates="prediction")  # noqa: F821
