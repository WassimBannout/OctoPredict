"""
Model evaluation: Brier Score, RPS (Ranked Probability Score), Accuracy.
"""
from __future__ import annotations

import numpy as np


def brier_score_multiclass(y_true_int: int, probas: list[float]) -> float:
    """Brier score for a single prediction (multiclass)."""
    n_classes = len(probas)
    total = 0.0
    for k in range(n_classes):
        indicator = 1.0 if k == y_true_int else 0.0
        total += (probas[k] - indicator) ** 2
    return total


def rps_score(y_true_int: int, probas: list[float]) -> float:
    """Ranked Probability Score for a single 3-outcome prediction."""
    n = len(probas)
    cum_pred = 0.0
    cum_true = 0.0
    rps = 0.0
    for k in range(n - 1):
        cum_pred += probas[k]
        cum_true += 1.0 if k >= y_true_int else 0.0
        rps += (cum_pred - cum_true) ** 2
    return rps / (n - 1)


def evaluate_predictions(
    y_true: np.ndarray,
    y_probas: np.ndarray,
) -> dict[str, float]:
    """Compute aggregate metrics over a validation set."""
    n = len(y_true)
    if n == 0:
        return {"brier": 0.0, "rps": 0.0, "accuracy": 0.0, "n": 0}

    brier_scores = []
    rps_scores = []
    correct = 0

    for yt, yp in zip(y_true, y_probas):
        brier_scores.append(brier_score_multiclass(int(yt), list(yp)))
        rps_scores.append(rps_score(int(yt), list(yp)))
        if int(np.argmax(yp)) == int(yt):
            correct += 1

    return {
        "brier": float(np.mean(brier_scores)),
        "rps": float(np.mean(rps_scores)),
        "accuracy": float(correct / n),
        "n": n,
    }
