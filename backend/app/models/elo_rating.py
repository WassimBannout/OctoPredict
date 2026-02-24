from datetime import datetime
from sqlalchemy import Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class EloRating(Base):
    __tablename__ = "elo_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), index=True)
    match_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("matches.id"), nullable=True, index=True)
    rating: Mapped[float] = mapped_column(Float, default=1500.0)
    rating_change: Mapped[float] = mapped_column(Float, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    team: Mapped["Team"] = relationship("Team", back_populates="elo_ratings")  # noqa: F821
    match: Mapped["Match | None"] = relationship("Match", back_populates="elo_ratings")  # noqa: F821
