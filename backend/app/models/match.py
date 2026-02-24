import enum
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class MatchStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    TIMED = "TIMED"
    IN_PLAY = "IN_PLAY"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


class MatchOutcome(str, enum.Enum):
    HOME_WIN = "HOME_WIN"
    DRAW = "DRAW"
    AWAY_WIN = "AWAY_WIN"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    competition_code: Mapped[str] = mapped_column(String(10), index=True)
    season: Mapped[str] = mapped_column(String(10), index=True)
    matchday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    utc_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus), default=MatchStatus.SCHEDULED)

    home_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), index=True)
    away_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), index=True)

    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[MatchOutcome | None] = mapped_column(Enum(MatchOutcome), nullable=True)

    # League table positions at time of match
    home_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    home_team: Mapped["Team"] = relationship("Team", back_populates="home_matches", foreign_keys=[home_team_id])  # noqa: F821
    away_team: Mapped["Team"] = relationship("Team", back_populates="away_matches", foreign_keys=[away_team_id])  # noqa: F821
    prediction: Mapped["Prediction | None"] = relationship("Prediction", back_populates="match", uselist=False)  # noqa: F821
    elo_ratings: Mapped[list["EloRating"]] = relationship("EloRating", back_populates="match")  # noqa: F821
