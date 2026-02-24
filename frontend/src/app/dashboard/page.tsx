"use client";
import { useState } from "react";
import { useUpcomingMatches } from "@/hooks/useMatches";
import { MatchCard } from "@/components/matches/MatchCard";
import { LeagueSelector } from "@/components/leagues/LeagueSelector";
import { ModelMetricsCard } from "@/components/stats/ModelMetricsCard";
import { AccuracyChart } from "@/components/stats/AccuracyChart";

export default function DashboardPage() {
  const [selectedLeague, setSelectedLeague] = useState<string | undefined>(undefined);
  const { data: matches, isLoading, error } = useUpcomingMatches(selectedLeague, 7);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Upcoming Matches</h1>
          <p className="text-slate-400 text-sm mt-1">Next 7 days · ML predictions powered by XGBoost</p>
        </div>
        <LeagueSelector selected={selectedLeague} onChange={setSelectedLeague} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main matches feed */}
        <div className="lg:col-span-3 space-y-4">
          {isLoading && (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-48 bg-slate-900 border border-slate-800 rounded-xl animate-pulse" />
              ))}
            </div>
          )}

          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-red-300">
              Failed to load matches. Is the backend running?
            </div>
          )}

          {matches && matches.length === 0 && (
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-8 text-center text-slate-400">
              No upcoming matches in the next 7 days.
            </div>
          )}

          {matches?.map((match) => (
            <MatchCard key={match.id} match={match} />
          ))}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <ModelMetricsCard />
          <AccuracyChart />
        </div>
      </div>
    </div>
  );
}
