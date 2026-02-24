"use client";
import { useState } from "react";
import { usePredictionHistory } from "@/hooks/usePredictions";
import { AccuracyChart } from "@/components/stats/AccuracyChart";
import { LeagueSelector } from "@/components/leagues/LeagueSelector";
import { PredictionBar } from "@/components/matches/PredictionBar";
import { formatDate, outcomeLabel, confidenceColor, leagueName, cn } from "@/lib/utils";

export default function PredictionsPage() {
  const [league, setLeague] = useState<string | undefined>();
  const [page, setPage] = useState(1);
  const { data, isLoading } = usePredictionHistory(page, 20, league);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Prediction History</h1>
          <p className="text-slate-400 text-sm mt-1">Historical predictions with resolution status</p>
        </div>
        <LeagueSelector selected={league} onChange={(c) => { setLeague(c); setPage(1); }} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 space-y-3">
          {isLoading && (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-32 bg-slate-900 border border-slate-800 rounded-xl animate-pulse" />
              ))}
            </div>
          )}

          {data?.items.map((pred) => {
            const m = pred.match;
            const resolved = pred.actual_outcome != null;
            const correct = pred.is_correct;

            return (
              <div
                key={pred.id}
                className={cn(
                  "bg-slate-900 border rounded-xl p-4 transition-colors",
                  resolved
                    ? correct
                      ? "border-green-800"
                      : "border-red-800"
                    : "border-slate-700"
                )}
              >
                {m && (
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                    <span>{leagueName(m.competition_code)} · MD{m.matchday ?? "?"}</span>
                    <span>{formatDate(m.utc_date)}</span>
                  </div>
                )}
                {m && (
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm">{m.home_team.short_name}</span>
                    {resolved ? (
                      <span className="text-sm font-bold tabular-nums">
                        {m.home_score ?? "?"} – {m.away_score ?? "?"}
                      </span>
                    ) : (
                      <span className="text-slate-500 text-sm">vs</span>
                    )}
                    <span className="font-semibold text-sm">{m.away_team.short_name}</span>
                  </div>
                )}

                <PredictionBar
                  probHome={pred.prob_home_win}
                  probDraw={pred.prob_draw}
                  probAway={pred.prob_away_win}
                  predictedOutcome={pred.predicted_outcome}
                  actualOutcome={pred.actual_outcome}
                />

                <div className="flex items-center justify-between text-xs mt-2">
                  <span>
                    Predicted: <span className="text-slate-200">{outcomeLabel(pred.predicted_outcome)}</span>
                  </span>
                  {resolved && (
                    <span className={correct ? "text-green-400 font-semibold" : "text-red-400 font-semibold"}>
                      {correct ? "✓ Correct" : "✗ Wrong"} · {outcomeLabel(pred.actual_outcome)}
                    </span>
                  )}
                  <span className={confidenceColor(pred.confidence)}>{pred.confidence}</span>
                </div>
              </div>
            );
          })}

          {/* Pagination */}
          {data && data.total > 20 && (
            <div className="flex justify-center gap-2 pt-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 bg-slate-800 rounded-lg text-sm disabled:opacity-40 hover:bg-slate-700"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-sm text-slate-400">
                Page {page} of {Math.ceil(data.total / 20)}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(data.total / 20)}
                className="px-4 py-2 bg-slate-800 rounded-lg text-sm disabled:opacity-40 hover:bg-slate-700"
              >
                Next
              </button>
            </div>
          )}
        </div>

        <div>
          <AccuracyChart />
        </div>
      </div>
    </div>
  );
}
