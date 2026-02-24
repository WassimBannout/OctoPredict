from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str] = mapped_column(String(100))
    tla: Mapped[str] = mapped_column(String(10))
    crest_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    competition_code: Mapped[str] = mapped_column(String(10), index=True)

    home_matches: Mapped[list["Match"]] = relationship("Match", back_populates="home_team", foreign_keys="Match.home_team_id")  # noqa: F821
    away_matches: Mapped[list["Match"]] = relationship("Match", back_populates="away_team", foreign_keys="Match.away_team_id")  # noqa: F821
    elo_ratings: Mapped[list["EloRating"]] = relationship("EloRating", back_populates="team")  # noqa: F821
