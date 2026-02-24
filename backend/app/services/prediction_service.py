"""
Prediction service: builds features, runs model (or Elo fallback),
stores predictions, and resolves them against actual results.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.match import Match, MatchStatus, MatchOutcome
from app.models.prediction import Prediction
from app.ml.features import build_features, FEATURE_NAMES
from app.ml.model import EloOnlyPredictor
from app.ml.model_store import ModelStore
from app.ml.evaluator import brier_score_multiclass, rps_score
from app.ml.model import OUTCOME_TO_INT
from app.services.elo_service import EloService
from app.services.elo_service import INITIAL_RATING as INITIAL_ELO
from app.utils.logging import get_logger

import numpy as np

logger = get_logger(__name__)


def _confidence(max_prob: float) -> str:
    if max_prob >= 0.60:
        return "HIGH"
    elif max_prob >= 0.45:
        return "MEDIUM"
    return "LOW"


class PredictionService:
    def __init__(self) -> None:
        self._store = ModelStore()
        self._elo_service = EloService()
        self._predictor = None
        self._model_meta: dict = {}
        self._model_loaded = False

    def _load_model(self):
        if not self._model_loaded:
            self._predictor, self._model_meta = self._store.load_latest()
            self._model_loaded = True

    def _current_model_version(self) -> str:
        self._load_model()
        if self._predictor is None:
            return "elo_fallback"
        return self._model_meta.get("version", "xgboost")

    async def predict_match(
        self,
        session: AsyncSession,
        match: Match,
    ) -> dict:
        """Generate prediction for a single match. Returns prediction dict."""
        self._load_model()
        fv = await build_features(session, match)
        feature_dict = fv.feature_dict

        # Try full XGBoost prediction
        if self._predictor is not None:
            try:
                expected_features = self._model_meta.get("feature_names") or list(FEATURE_NAMES)
                X = np.array(
                    [[float(feature_dict.get(name, 0.0)) for name in expected_features]],
                    dtype=np.float32,
                )
                probas = self._predictor.predict_proba(X)[0]
                ph, pd_, pa = float(probas[0]), float(probas[1]), float(probas[2])
                model_version = self._model_meta.get("version", "xgboost")
                model_type = "xgboost"
            except Exception as e:
                logger.warning(f"XGBoost prediction failed for match {match.id}: {e}. Falling back to Elo.")
                ph = pd_ = pa = None
        else:
            ph = pd_ = pa = None

        if ph is None or pd_ is None or pa is None:
            # Elo fallback
            current_ratings = await self._elo_service.get_current_ratings(session)
            elo_h = current_ratings.get(match.home_team_id, INITIAL_ELO)
            elo_a = current_ratings.get(match.away_team_id, INITIAL_ELO)
            ph, pd_, pa = EloOnlyPredictor.predict_proba(elo_h, elo_a)
            # Preserve full engineered features but ensure Elo values are accurate at prediction time.
            feature_dict["elo_home"] = elo_h
            feature_dict["elo_away"] = elo_a
            feature_dict["elo_diff"] = elo_h - elo_a
            model_version = "elo_fallback"
            model_type = "elo_fallback"

        # Determine predicted outcome
        max_prob = max(ph, pd_, pa)
        if ph == max_prob:
            predicted_outcome = MatchOutcome.HOME_WIN
        elif pd_ == max_prob:
            predicted_outcome = MatchOutcome.DRAW
        else:
            predicted_outcome = MatchOutcome.AWAY_WIN

        return {
            "prob_home_win": round(ph, 4),
            "prob_draw": round(pd_, 4),
            "prob_away_win": round(pa, 4),
            "predicted_outcome": predicted_outcome,
            "confidence": _confidence(max_prob),
            "features_snapshot": feature_dict,
            "model_version": model_version,
            "model_type": model_type,
        }

    async def generate_upcoming_predictions(
        self,
        force_refresh: bool = False,
        stale_only: bool = True,
    ) -> int:
        """Generate or refresh predictions for upcoming scheduled matches."""
        days_ahead = 14
        cutoff = datetime.utcnow() + timedelta(days=days_ahead)
        now = datetime.utcnow()
        count = 0
        current_version = self._current_model_version()

        async with AsyncSessionLocal() as session:
            stmt = (
                select(Match)
                .where(Match.status.in_([MatchStatus.SCHEDULED, MatchStatus.TIMED]))
                .where(Match.utc_date >= now)
                .where(Match.utc_date <= cutoff)
            )
            matches = list(await session.scalars(stmt))

            for match in matches:
                existing = await session.scalar(
                    select(Prediction).where(Prediction.match_id == match.id)
                )
                if existing is not None:
                    if not force_refresh:
                        continue
                    if stale_only and existing.model_version == current_version:
                        continue

                try:
                    pred_data = await self.predict_match(session, match)

                    if existing is None:
                        pred = Prediction(
                            match_id=match.id,
                            prob_home_win=pred_data["prob_home_win"],
                            prob_draw=pred_data["prob_draw"],
                            prob_away_win=pred_data["prob_away_win"],
                            predicted_outcome=pred_data["predicted_outcome"],
                            confidence=pred_data["confidence"],
                            features_snapshot=pred_data["features_snapshot"],
                            model_version=pred_data["model_version"],
                            predicted_at=datetime.utcnow(),
                        )
                        session.add(pred)
                    else:
                        existing.prob_home_win = pred_data["prob_home_win"]
                        existing.prob_draw = pred_data["prob_draw"]
                        existing.prob_away_win = pred_data["prob_away_win"]
                        existing.predicted_outcome = pred_data["predicted_outcome"]
                        existing.confidence = pred_data["confidence"]
                        existing.features_snapshot = pred_data["features_snapshot"]
                        existing.model_version = pred_data["model_version"]
                        existing.predicted_at = datetime.utcnow()
                    count += 1
                except Exception as e:
                    logger.error(f"Failed prediction for match {match.id}: {e}")

            await session.commit()

        logger.info(f"Generated {count} predictions.")
        return count

    async def resolve_predictions(self) -> int:
        """Update predictions with actual outcomes for finished matches."""
        count = 0
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Prediction)
                .join(Match, Prediction.match_id == Match.id)
                .where(Match.status == MatchStatus.FINISHED)
                .where(Prediction.actual_outcome.is_(None))
            )
            predictions = list(await session.scalars(stmt))

            for pred in predictions:
                match = await session.get(Match, pred.match_id)
                if match is None or match.outcome is None:
                    continue

                pred.actual_outcome = match.outcome
                pred.is_correct = pred.predicted_outcome == match.outcome

                # Compute scoring metrics
                y_true = OUTCOME_TO_INT.get(match.outcome)
                if y_true is not None:
                    probas = [pred.prob_home_win, pred.prob_draw, pred.prob_away_win]
                    pred.brier_score = brier_score_multiclass(y_true, probas)
                    pred.rps_score = rps_score(y_true, probas)

                count += 1

            await session.commit()

        logger.info(f"Resolved {count} predictions.")
        return count
