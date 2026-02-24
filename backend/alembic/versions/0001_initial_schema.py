"""initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("short_name", sa.String(100), nullable=False),
        sa.Column("tla", sa.String(10), nullable=False),
        sa.Column("crest_url", sa.String(500), nullable=True),
        sa.Column("competition_code", sa.String(10), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_teams_external_id", "teams", ["external_id"])
    op.create_index("ix_teams_competition_code", "teams", ["competition_code"])

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("competition_code", sa.String(10), nullable=False),
        sa.Column("season", sa.String(10), nullable=False),
        sa.Column("matchday", sa.Integer(), nullable=True),
        sa.Column("utc_date", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="SCHEDULED"),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(20), nullable=True),
        sa.Column("home_position", sa.Integer(), nullable=True),
        sa.Column("away_position", sa.Integer(), nullable=True),
        sa.Column("home_points", sa.Integer(), nullable=True),
        sa.Column("away_points", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_matches_external_id", "matches", ["external_id"])
    op.create_index("ix_matches_competition_code", "matches", ["competition_code"])
    op.create_index("ix_matches_utc_date", "matches", ["utc_date"])
    op.create_index("ix_matches_home_team_id", "matches", ["home_team_id"])
    op.create_index("ix_matches_away_team_id", "matches", ["away_team_id"])
    op.create_index("ix_matches_season", "matches", ["season"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("prob_home_win", sa.Float(), nullable=False),
        sa.Column("prob_draw", sa.Float(), nullable=False),
        sa.Column("prob_away_win", sa.Float(), nullable=False),
        sa.Column("predicted_outcome", sa.String(20), nullable=False),
        sa.Column("confidence", sa.String(10), nullable=False),
        sa.Column("features_snapshot", sa.JSON(), nullable=True),
        sa.Column("actual_outcome", sa.String(20), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("brier_score", sa.Float(), nullable=True),
        sa.Column("rps_score", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=False, server_default="elo_fallback"),
        sa.Column("predicted_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id"),
    )
    op.create_index("ix_predictions_match_id", "predictions", ["match_id"])

    op.create_table(
        "elo_ratings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=True),
        sa.Column("rating", sa.Float(), nullable=False, server_default="1500.0"),
        sa.Column("rating_change", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_elo_ratings_team_id", "elo_ratings", ["team_id"])
    op.create_index("ix_elo_ratings_match_id", "elo_ratings", ["match_id"])
    op.create_index("ix_elo_ratings_recorded_at", "elo_ratings", ["recorded_at"])

    op.create_table(
        "job_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_logs_job_name", "job_logs", ["job_name"])


def downgrade() -> None:
    op.drop_table("job_logs")
    op.drop_table("elo_ratings")
    op.drop_table("predictions")
    op.drop_table("matches")
    op.drop_table("teams")
