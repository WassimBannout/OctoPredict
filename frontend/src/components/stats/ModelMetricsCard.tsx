"use client";
import { useModelStats, useOverviewStats } from "@/hooks/useLeagueStats";

export function ModelMetricsCard() {
  const { data: model } = useModelStats();
  const { data: overview } = useOverviewStats();
  const valAcc = model?.metrics?.accuracy;
  const eloAcc = model?.metrics?.baseline_elo_accuracy;
  const upliftVsElo =
    typeof valAcc === "number" && typeof eloAcc === "number"
      ? (valAcc - eloAcc) * 100
      : null;

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">Model Overview</h3>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <Stat
          label="Model"
          value={model ? (model.model_type === "xgboost" ? "XGBoost" : "Elo Fallback") : "—"}
        />
        <Stat
          label="Accuracy"
          value={overview?.overall_accuracy != null ? `${(overview.overall_accuracy * 100).toFixed(1)}%` : "—"}
        />
        <Stat
          label="Predictions"
          value={overview ? String(overview.total_predictions) : "—"}
        />
        <Stat
          label="Resolved"
          value={overview ? String(overview.resolved_predictions) : "—"}
        />
        <Stat
          label="Val Accuracy"
          value={typeof valAcc === "number" ? `${(valAcc * 100).toFixed(1)}%` : "—"}
        />
        <Stat
          label="Vs Elo"
          value={upliftVsElo != null ? `${upliftVsElo >= 0 ? "+" : ""}${upliftVsElo.toFixed(1)}pp` : "—"}
        />
        {model?.metrics && (
          <>
            <Stat
              label="Brier"
              value={model.metrics.brier != null ? model.metrics.brier.toFixed(3) : "—"}
            />
            <Stat
              label="RPS"
              value={model.metrics.rps != null ? model.metrics.rps.toFixed(3) : "—"}
            />
          </>
        )}
      </div>
      {model && (
        <p className="text-xs text-slate-500 mt-3">v{model.version}</p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="font-semibold text-slate-100">{value}</div>
    </div>
  );
}
