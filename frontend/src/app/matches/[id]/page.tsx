"use client";
import { use, useEffect, useState } from "react";
import { getMatch, getMatchFeatures } from "@/lib/api";
import type { Match } from "@/lib/types";
import { formatDate, formatTime, formatElo, outcomeLabel, leagueName } from "@/lib/utils";
import { PredictionBar } from "@/components/matches/PredictionBar";
import Image from "next/image";
import Link from "next/link";

export default function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [match, setMatch] = useState<Match | null>(null);
  const [features, setFeatures] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMatch(Number(id)).then(setMatch).catch((e) => setError(e.message));
    getMatchFeatures(Number(id))
      .then((d) => setFeatures(d.features))
      .catch(() => {});
  }, [id]);

  if (error) return <div className="text-red-400 p-4">{error}</div>;
  if (!match) return <div className="h-64 bg-slate-900 rounded-xl animate-pulse" />;

  const pred = match.prediction;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-sm text-slate-400">
        <Link href="/dashboard" className="hover:text-white">Dashboard</Link> →{" "}
        <span>{leagueName(match.competition_code)}</span>
      </div>

      <div className="bg-slate-900 border border-slate-700 rounded-xl p-6">
        <div className="text-center text-xs text-slate-400 mb-4">
          {leagueName(match.competition_code)} · Matchday {match.matchday ?? "?"} ·{" "}
          {formatDate(match.utc_date)} {formatTime(match.utc_date)}
        </div>

        <div className="grid grid-cols-3 items-center gap-4 mb-6">
          <TeamDisplay team={match.home_team} elo={match.home_elo} />
          <div className="text-center">
            {match.status === "FINISHED" ? (
              <div>
                <div className="text-3xl font-bold tabular-nums">
                  {match.home_score} – {match.away_score}
                </div>
                <div className="text-xs text-slate-400 mt-1">{outcomeLabel(match.outcome)}</div>
              </div>
            ) : (
              <div className="text-slate-500 text-xl font-medium">vs</div>
            )}
          </div>
          <TeamDisplay team={match.away_team} elo={match.away_elo} />
        </div>

        {pred && (
          <div className="border-t border-slate-700 pt-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Prediction</h3>
            <PredictionBar
              probHome={pred.prob_home_win}
              probDraw={pred.prob_draw}
              probAway={pred.prob_away_win}
              predictedOutcome={pred.predicted_outcome}
              actualOutcome={match.outcome}
            />
            <div className="flex justify-between text-xs text-slate-400 mt-2">
              <span>Confidence: <span className="text-white">{pred.confidence}</span></span>
              <span>{pred.model_version}</span>
            </div>
          </div>
        )}
      </div>

      {/* Feature transparency */}
      {features && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Feature Transparency</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {Object.entries(features).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span className="text-slate-400">{key}</span>
                <span className="text-slate-200 tabular-nums">{typeof value === "number" ? value.toFixed(2) : value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TeamDisplay({ team, elo }: { team: Match["home_team"]; elo?: number | null }) {
  return (
    <div className="flex flex-col items-center gap-2">
      {team.crest_url && (
        <div className="relative h-16 w-16">
          <Image src={team.crest_url} alt={team.tla} fill className="object-contain" />
        </div>
      )}
      <span className="font-semibold text-center">{team.short_name}</span>
      <span className="text-xs text-blue-400">{formatElo(elo)} Elo</span>
    </div>
  );
}
