"use client";
import { use, useState } from "react";
import { useStandings } from "@/hooks/useLeagueStats";
import { useUpcomingMatches } from "@/hooks/useMatches";
import { StandingsTable } from "@/components/leagues/StandingsTable";
import { MatchCard } from "@/components/matches/MatchCard";
import { leagueName } from "@/lib/utils";
import type { StandingRow } from "@/lib/types";

export default function LeaguePage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = use(params);
  const { data: standingsData, isLoading: standingsLoading } = useStandings(code);
  const { data: matches, isLoading: matchesLoading } = useUpcomingMatches(code, 14);
  const [tab, setTab] = useState<"standings" | "fixtures">("fixtures");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{leagueName(code)}</h1>
        <p className="text-slate-400 text-sm mt-1">Standings · Upcoming Fixtures · Predictions</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-700">
        {(["fixtures", "standings"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              tab === t
                ? "border-blue-500 text-white"
                : "border-transparent text-slate-400 hover:text-white"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "fixtures" && (
        <div className="space-y-4">
          {matchesLoading && (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-48 bg-slate-900 border border-slate-800 rounded-xl animate-pulse" />
              ))}
            </div>
          )}
          {matches?.map((m) => <MatchCard key={m.id} match={m} />)}
          {matches?.length === 0 && (
            <p className="text-slate-400 text-center py-8">No upcoming fixtures in the next 14 days.</p>
          )}
        </div>
      )}

      {tab === "standings" && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
          {standingsLoading && <div className="h-64 animate-pulse bg-slate-800 rounded" />}
          {standingsData && (
            <StandingsTable standings={standingsData.standings as StandingRow[]} />
          )}
        </div>
      )}
    </div>
  );
}
