"""
Temporal train/val split trainer.
- Loads all finished matches with outcomes from DB
- Builds feature vectors (no data leakage)
- 80/20 chronological split
- Trains XGBoost + isotonic calibration
- Saves versioned model
"""
from __future__ import annotations

import numpy as np
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.match import Match, MatchStatus
from app.ml.features import build_features, FEATURE_NAMES
from app.ml.model import XGBoostPredictor, OUTCOME_TO_INT, EloOnlyPredictor
from app.ml.evaluator import evaluate_predictions
from app.ml.model_store import ModelStore
from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ModelTrainer:
    async def train(self) -> str | None:
        """Train model. Returns model version string or None if insufficient data."""
        logger.info("Starting model training...")

        async with AsyncSessionLocal() as session:
            stmt = (
                select(Match)
                .where(Match.status == MatchStatus.FINISHED)
                .where(Match.outcome.isnot(None))
                .order_by(Match.utc_date)
            )
            matches = list(await session.scalars(stmt))

        n = len(matches)
        logger.info(f"Found {n} finished matches for training.")

        if n < settings.min_training_samples:
            logger.warning(f"Insufficient training data ({n} < {settings.min_training_samples}). Using EloFallback.")
            return None

        # Build feature matrix
        X_list = []
        y_list = []

        async with AsyncSessionLocal() as session:
            for match in matches:
                try:
                    fv = await build_features(session, match)
                    X_list.append(fv.features)
                    y_list.append(OUTCOME_TO_INT[match.outcome])
                except Exception as e:
                    logger.debug(f"Skipping match {match.id}: {e}")

        if len(X_list) < settings.min_training_samples:
            logger.warning("Too few valid feature vectors. Skipping training.")
            return None

        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.int32)

        # Temporal 80/20 split
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}")

        # Small search over robust configs; pick best by validation accuracy then Brier.
        candidates = [
            {
                "name": "balanced_default",
                "params": {
                    "n_estimators": 500,
                    "max_depth": 5,
                    "learning_rate": 0.05,
                    "subsample": 0.85,
                    "colsample_bytree": 0.85,
                    "min_child_weight": 2,
                    "reg_alpha": 0.0,
                    "reg_lambda": 1.2,
                    "gamma": 0.05,
                },
            },
            {
                "name": "regularized",
                "params": {
                    "n_estimators": 700,
                    "max_depth": 4,
                    "learning_rate": 0.03,
                    "subsample": 0.9,
                    "colsample_bytree": 0.9,
                    "min_child_weight": 3,
                    "reg_alpha": 0.05,
                    "reg_lambda": 1.5,
                    "gamma": 0.1,
                },
            },
            {
                "name": "shallow_fast",
                "params": {
                    "n_estimators": 360,
                    "max_depth": 3,
                    "learning_rate": 0.06,
                    "subsample": 0.9,
                    "colsample_bytree": 0.9,
                    "min_child_weight": 2,
                    "reg_alpha": 0.0,
                    "reg_lambda": 1.0,
                    "gamma": 0.1,
                },
            },
        ]

        best_predictor = None
        best_metrics = None
        best_name = None

        for candidate in candidates:
            logger.info(f"Training candidate: {candidate['name']}")
            predictor = XGBoostPredictor(
                xgb_params=candidate["params"],
                calibration_method="sigmoid",
            )
            predictor.fit(X_train, y_train, X_val, y_val)
            val_probas = predictor.predict_proba(X_val)
            metrics = evaluate_predictions(y_val, val_probas)
            logger.info(f"Candidate {candidate['name']} metrics: {metrics}")

            if best_metrics is None:
                best_predictor = predictor
                best_metrics = metrics
                best_name = candidate["name"]
                continue

            if (
                metrics["accuracy"] > best_metrics["accuracy"]
                or (
                    metrics["accuracy"] == best_metrics["accuracy"]
                    and metrics["brier"] < best_metrics["brier"]
                )
            ):
                best_predictor = predictor
                best_metrics = metrics
                best_name = candidate["name"]

        if best_predictor is None or best_metrics is None:
            logger.error("No valid model candidate produced metrics.")
            return None

        # Baselines on the same validation split for honest comparison.
        majority_class = int(np.bincount(y_train).argmax())
        majority_accuracy = float(np.mean(y_val == majority_class))

        idx_elo_home = FEATURE_NAMES.index("elo_home")
        idx_elo_away = FEATURE_NAMES.index("elo_away")
        elo_pred = []
        for row in X_val:
            ph, pd_, pa = EloOnlyPredictor.predict_proba(
                float(row[idx_elo_home]),
                float(row[idx_elo_away]),
            )
            elo_pred.append(int(np.argmax([ph, pd_, pa])))
        elo_accuracy = float(np.mean(np.array(elo_pred, dtype=np.int32) == y_val))

        best_metrics["baseline_majority_accuracy"] = majority_accuracy
        best_metrics["baseline_elo_accuracy"] = elo_accuracy
        best_metrics["uplift_vs_majority_pp"] = (best_metrics["accuracy"] - majority_accuracy) * 100.0
        best_metrics["uplift_vs_elo_pp"] = (best_metrics["accuracy"] - elo_accuracy) * 100.0

        logger.info(f"Selected candidate: {best_name} with metrics: {best_metrics}")
        store = ModelStore()
        existing_versions = store.list_versions()
        best_existing = None
        for meta in existing_versions:
            metrics = meta.get("metrics", {}) if isinstance(meta, dict) else {}
            acc = metrics.get("accuracy")
            brier = metrics.get("brier")
            if acc is None:
                continue
            candidate = (float(acc), -float(brier) if brier is not None else float("-inf"), str(meta.get("created_at", "")), meta)
            if best_existing is None or candidate > best_existing:
                best_existing = candidate

        if best_existing is not None:
            existing_acc = best_existing[0]
            existing_brier = -best_existing[1] if best_existing[1] != float("-inf") else None
            if (
                best_metrics["accuracy"] < existing_acc
                and (existing_brier is None or best_metrics["brier"] >= existing_brier)
            ):
                existing_meta = best_existing[3]
                existing_version = existing_meta.get("version", "unknown")
                logger.info(
                    "New model underperforms existing best (%s acc=%.4f). Keeping existing model.",
                    existing_version,
                    existing_acc,
                )
                return existing_version

        # Save model
        version = store.save(best_predictor, best_metrics, list(FEATURE_NAMES))
        logger.info(f"Model saved as version {version}")
        return version
