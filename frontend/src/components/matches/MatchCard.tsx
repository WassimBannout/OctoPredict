"use client";
import Image from "next/image";
import Link from "next/link";
import type { Match } from "@/lib/types";
import { formatDate, formatTime, formatElo, confidenceColor, outcomeLabel, leagueName, pct, cn } from "@/lib/utils";
import { TeamFormStrip } from "./TeamFormStrip";
import { PredictionBar } from "./PredictionBar";

interface MatchCardProps {
  match: Match;
}

const statusBadge = (status: string, outcome: string | null) => {
  if (status === "FINISHED") {
    return (
      <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded">
        {outcomeLabel(outcome)}
      </span>
    );
  }
  if (status === "IN_PLAY" || status === "PAUSED") {
    return <span className="text-xs bg-green-900 text-green-300 px-2 py-0.5 rounded animate-pulse">LIVE</span>;
  }
  return null;
};

export function MatchCard({ match }: MatchCardProps) {
  const pred = match.prediction;
  const isFinished = match.status === "FINISHED";

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 hover:border-slate-500 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between text-xs text-slate-400 mb-3">
        <span>
          {leagueName(match.competition_code)} · MD{match.matchday ?? "?"}
        </span>
        <div className="flex items-center gap-2">
          {statusBadge(match.status, match.outcome)}
          <span>{formatDate(match.utc_date)}</span>
          <span>{formatTime(match.utc_date)}</span>
        </div>
      </div>

      {/* Teams Row */}
      <div className="grid grid-cols-3 items-center gap-4 mb-3">
        {/* Home */}
        <div className="flex flex-col items-center text-center gap-1">
          {match.home_team.crest_url && (
            <div className="relative h-10 w-10">
              <Image
                src={match.home_team.crest_url}
                alt={match.home_team.tla}
                fill
                className="object-contain"
              />
            </div>
          )}
          <span className="font-semibold text-sm">{match.home_team.short_name}</span>
          <span className="text-xs text-blue-400">{formatElo(match.home_elo)} Elo</span>
        </div>

        {/* Score / VS */}
        <div className="text-center">
          {isFinished ? (
            <span className="text-2xl font-bold tabular-nums">
              {match.home_score ?? 0} – {match.away_score ?? 0}
            </span>
          ) : (
            <span className="text-slate-500 text-lg font-medium">vs</span>
          )}
        </div>

        {/* Away */}
        <div className="flex flex-col items-center text-center gap-1">
          {match.away_team.crest_url && (
            <div className="relative h-10 w-10">
              <Image
                src={match.away_team.crest_url}
                alt={match.away_team.tla}
                fill
                className="object-contain"
              />
            </div>
          )}
          <span className="font-semibold text-sm">{match.away_team.short_name}</span>
          <span className="text-xs text-blue-400">{formatElo(match.away_elo)} Elo</span>
        </div>
      </div>

      {/* Prediction Bar */}
      {pred && (
        <div className="mt-2">
          <PredictionBar
            probHome={pred.prob_home_win}
            probDraw={pred.prob_draw}
            probAway={pred.prob_away_win}
            predictedOutcome={pred.predicted_outcome}
            actualOutcome={match.outcome}
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1.5">
            <span>
              Confidence:{" "}
              <span className={confidenceColor(pred.confidence)}>{pred.confidence}</span>
            </span>
            <span className="text-slate-500">
              {pred.model_version.startsWith("xgboost") ? "XGBoost" : "Elo Fallback"}
            </span>
          </div>
        </div>
      )}

      {/* Link */}
      <div className="mt-3 text-right">
        <Link href={`/matches/${match.id}`} className="text-xs text-blue-400 hover:text-blue-300">
          Details →
        </Link>
      </div>
    </div>
  );
}
