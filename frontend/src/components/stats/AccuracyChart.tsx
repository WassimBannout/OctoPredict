"use client";
import { useAccuracyStats } from "@/hooks/usePredictions";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";

// 3-way random baseline: 33%. Top published models: 52–57%. Bookmakers: ~52–55%.
const RANDOM_BASELINE = 0.333;

export function AccuracyChart() {
  const { data } = useAccuracyStats();

  if (!data) return <div className="h-40 bg-slate-800 rounded animate-pulse" />;

  const isLive = data.accuracy_source === "resolved_predictions";
  const isValidation = data.accuracy_source === "model_validation";

  // Green for live results, yellow for validation estimate, slate for no data
  const accuracyColor = isLive ? "text-green-400" : isValidation ? "text-yellow-400" : "text-slate-400";

  const chartData = [
    { name: "Correct", value: data.correct_predictions, color: "#22c55e" },
    { name: "Wrong", value: data.resolved_predictions - data.correct_predictions, color: "#ef4444" },
    { name: "Pending", value: data.total_predictions - data.resolved_predictions, color: "#64748b" },
  ];

  const brier = data.avg_brier_score ?? data.validation_brier_score;
  const rps = data.avg_rps_score ?? data.validation_rps_score;

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-slate-300 mb-1">Prediction Accuracy</h3>

      <div className="flex items-end gap-2 mb-1">
        <p className={`text-2xl font-bold ${accuracyColor}`}>
          {data.display_accuracy != null
            ? `${(data.display_accuracy * 100).toFixed(1)}%`
            : "No data"}
        </p>
        {/* Baseline comparison */}
        {data.display_accuracy != null && (
          <p className="text-xs text-slate-500 mb-1">
            vs {(RANDOM_BASELINE * 100).toFixed(0)}% random
          </p>
        )}
      </div>

      {/* Source badge */}
      <p className="text-xs mb-3">
        {isLive && (
          <span className="text-green-500">● Live</span>
        )}
        {isValidation && (
          <span className="text-yellow-500">
            ◐ Validation estimate{data.validation_samples ? ` · n=${data.validation_samples}` : ""}
          </span>
        )}
        {!isLive && !isValidation && (
          <span className="text-slate-500">Awaiting resolved predictions</span>
        )}
      </p>

      {/* Bar chart — only meaningful once live predictions exist */}
      {data.total_predictions > 0 && (
        <ResponsiveContainer width="100%" height={100}>
          <BarChart data={chartData} barSize={28}>
            <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis hide />
            <Tooltip
              contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {/* Scoring metrics */}
      {(brier != null || rps != null) && (
        <div className="flex gap-4 text-xs text-slate-400 mt-2 pt-2 border-t border-slate-800">
          {brier != null && (
            <span title="Brier score: lower is better. Perfect = 0, random ≈ 0.67">
              Brier: <span className="text-slate-200">{brier.toFixed(3)}</span>
            </span>
          )}
          {rps != null && (
            <span title="Ranked Probability Score: lower is better">
              RPS: <span className="text-slate-200">{rps.toFixed(3)}</span>
            </span>
          )}
        </div>
      )}

      {/* Context note for validation accuracy */}
      {isValidation && (
        <p className="text-xs text-slate-500 mt-2 leading-relaxed">
          52–55% is competitive — bookmakers average ~53% on 3-way outcomes.
        </p>
      )}
    </div>
  );
}
