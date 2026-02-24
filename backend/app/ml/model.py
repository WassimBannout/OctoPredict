"""
XGBoost + isotonic calibration model wrapper.
Also defines the EloOnlyPredictor cold-start fallback.
"""
from __future__ import annotations

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
try:
    # sklearn >= 1.6 replacement for cv="prefit"
    from sklearn.frozen import FrozenEstimator
except Exception:  # pragma: no cover - compatibility fallback
    FrozenEstimator = None
from xgboost import XGBClassifier

from app.models.match import MatchOutcome
from app.utils.logging import get_logger

logger = get_logger(__name__)

OUTCOME_CLASSES = [MatchOutcome.HOME_WIN, MatchOutcome.DRAW, MatchOutcome.AWAY_WIN]
OUTCOME_TO_INT = {MatchOutcome.HOME_WIN: 0, MatchOutcome.DRAW: 1, MatchOutcome.AWAY_WIN: 2}
INT_TO_OUTCOME = {0: MatchOutcome.HOME_WIN, 1: MatchOutcome.DRAW, 2: MatchOutcome.AWAY_WIN}

HOME_ADVANTAGE = 100.0


class XGBoostPredictor:
    """XGBoost multi-class with configurable probability calibration."""

    def __init__(
        self,
        xgb_params: dict | None = None,
        calibration_method: str = "sigmoid",
    ) -> None:
        params = {
            "objective": "multi:softprob",
            "num_class": 3,
            "n_estimators": 500,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 1,
            "reg_alpha": 0.0,
            "reg_lambda": 1.0,
            "gamma": 0.0,
            "eval_metric": "mlogloss",
            "early_stopping_rounds": 30,
            "random_state": 42,
            "n_jobs": -1,
        }
        if xgb_params:
            params.update(xgb_params)

        base = XGBClassifier(**params)
        self.model = None
        self._base = base
        self.calibration_method = calibration_method
        self.is_fitted = False

    def fit(self, X_train, y_train, X_val, y_val) -> None:
        self._base.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        if FrozenEstimator is not None:
            calibrator_base = FrozenEstimator(self._base)
            self.model = CalibratedClassifierCV(calibrator_base, method=self.calibration_method, cv=None)
        else:
            self.model = CalibratedClassifierCV(self._base, method=self.calibration_method, cv="prefit")
        self.model.fit(X_val, y_val)
        self.is_fitted = True

    def predict_proba(self, X) -> np.ndarray:
        """Returns array of shape (n_samples, 3) → [home_win, draw, away_win]."""
        if self.model is None:
            raise RuntimeError("Model is not fitted.")
        return self.model.predict_proba(X)

    def predict(self, X) -> list[MatchOutcome]:
        probas = self.predict_proba(X)
        return [INT_TO_OUTCOME[int(np.argmax(p))] for p in probas]

    def feature_importances(self, feature_names: list[str]) -> dict[str, float]:
        imp = self._base.feature_importances_
        total = imp.sum() or 1.0
        return {name: float(v / total) for name, v in zip(feature_names, imp)}


def _elo_expected(home_rating: float, away_rating: float) -> float:
    """Expected score for home team (with home advantage)."""
    return 1.0 / (1.0 + 10.0 ** ((away_rating - (home_rating + HOME_ADVANTAGE)) / 400.0))


class EloOnlyPredictor:
    """
    Cold-start fallback: converts Elo ratings into 3-way probabilities
    using the logistic Elo formula.
    """

    @staticmethod
    def predict_proba(elo_home: float, elo_away: float) -> tuple[float, float, float]:
        """Returns (prob_home_win, prob_draw, prob_away_win)."""
        exp_home = _elo_expected(elo_home, elo_away)
        exp_away = 1.0 - exp_home

        # Approximate draw probability: peaks when exp_home ≈ 0.5
        draw_prob = 0.30 * (1.0 - abs(exp_home - 0.5) * 2.0)
        draw_prob = max(0.10, min(0.35, draw_prob))

        # Remaining probability split proportionally
        remaining = 1.0 - draw_prob
        home_prob = exp_home * remaining
        away_prob = exp_away * remaining

        total = home_prob + draw_prob + away_prob
        return home_prob / total, draw_prob / total, away_prob / total
