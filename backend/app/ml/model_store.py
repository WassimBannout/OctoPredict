"""
Versioned model persistence using joblib.
Models saved as model_{timestamp}.joblib with a metadata sidecar.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib

from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ModelStore:
    def __init__(self, model_dir: str | None = None) -> None:
        self.model_dir = Path(model_dir or settings.model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def save(self, predictor, metrics: dict, feature_names: list[str]) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        version = f"xgboost_{ts}"
        model_path = self.model_dir / f"model_{ts}.joblib"
        meta_path = self.model_dir / f"model_{ts}.json"

        joblib.dump(predictor, model_path)

        meta = {
            "version": version,
            "created_at": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "feature_names": feature_names,
            "model_type": "xgboost",
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Model saved: {model_path}")
        return version

    def _best_model_path(self) -> Path | None:
        """
        Select best model by validation metrics when available.
        Falls back to latest timestamped model if metadata is missing.
        """
        model_files = sorted(self.model_dir.glob("model_*.joblib"))
        if not model_files:
            return None

        best: tuple[float, float, str, Path] | None = None
        for model_path in model_files:
            meta_path = model_path.with_suffix(".json")
            acc = float("-inf")
            brier = float("inf")
            created_at = ""

            if meta_path.exists():
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    metrics = meta.get("metrics", {}) if isinstance(meta, dict) else {}
                    if isinstance(metrics, dict):
                        if metrics.get("accuracy") is not None:
                            acc = float(metrics["accuracy"])
                        if metrics.get("brier") is not None:
                            brier = float(metrics["brier"])
                    created_at = str(meta.get("created_at", ""))
                except Exception:
                    pass

            candidate = (acc, -brier, created_at, model_path)
            if best is None or candidate > best:
                best = candidate

        return best[3] if best else model_files[-1]

    def load_latest(self):
        """Load the best available model. Returns (predictor, metadata) or (None, None)."""
        selected = self._best_model_path()
        if selected is None:
            return None, None

        meta_path = selected.with_suffix(".json")

        try:
            predictor = joblib.load(selected)
            meta = {}
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
            logger.info(f"Loaded model: {selected.name}")
            return predictor, meta
        except Exception as e:
            logger.error(f"Failed to load model {selected}: {e}")
            return None, None

    def list_versions(self) -> list[dict]:
        metas = []
        for meta_path in sorted(self.model_dir.glob("model_*.json")):
            try:
                with open(meta_path) as f:
                    metas.append(json.load(f))
            except Exception:
                pass
        return metas
