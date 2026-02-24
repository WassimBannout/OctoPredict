"use client";
import { use, useEffect, useState } from "react";
import { getTeam } from "@/lib/api";
import type { TeamDetail } from "@/lib/types";
import { formatElo, leagueName } from "@/lib/utils";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { TeamFormStrip } from "@/components/matches/TeamFormStrip";
import Image from "next/image";

export default function TeamPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [team, setTeam] = useState<TeamDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTeam(Number(id))
      .then(setTeam)
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="text-red-400 p-4">{error}</div>;
  if (!team) return <div className="h-64 bg-slate-900 rounded-xl animate-pulse" />;

  const eloChartData = team.elo_history.slice(-20).map((p) => ({
    date: p.date.slice(0, 10),
    rating: Math.round(p.rating),
  }));

  const lastResults = team.last_5_matches.map((m) => m.result);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        {team.crest_url && (
          <div className="relative h-16 w-16">
            <Image src={team.crest_url} alt={team.tla} fill className="object-contain" />
          </div>
        )}
        <div>
          <h1 className="text-2xl font-bold">{team.name}</h1>
          <p className="text-slate-400 text-sm">{leagueName(team.competition_code)} · {team.tla}</p>
          <p className="text-blue-400 font-semibold mt-1">Elo: {formatElo(team.current_elo)}</p>
        </div>
      </div>

      {/* Elo History Chart */}
      {eloChartData.length > 1 && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Elo Rating History (last 20 matches)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={eloChartData}>
              <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis domain={["auto", "auto"]} tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
                labelStyle={{ color: "#94a3b8" }}
              />
              <Line type="monotone" dataKey="rating" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Records */}
      <div className="grid grid-cols-2 gap-4">
        <RecordCard title="Home Record" record={team.home_record} />
        <RecordCard title="Away Record" record={team.away_record} />
      </div>

      {/* Form */}
      {lastResults.length > 0 && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-2">Last 5 Results</h3>
          <TeamFormStrip results={lastResults} />
        </div>
      )}
    </div>
  );
}

function RecordCard({ title, record }: { title: string; record: Record<string, number> }) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-slate-300 mb-2">{title}</h3>
      <div className="flex gap-4 text-sm">
        <div className="text-center">
          <div className="text-green-400 font-bold text-lg">{record.wins ?? 0}</div>
          <div className="text-slate-400 text-xs">W</div>
        </div>
        <div className="text-center">
          <div className="text-yellow-400 font-bold text-lg">{record.draws ?? 0}</div>
          <div className="text-slate-400 text-xs">D</div>
        </div>
        <div className="text-center">
          <div className="text-red-400 font-bold text-lg">{record.losses ?? 0}</div>
          <div className="text-slate-400 text-xs">L</div>
        </div>
      </div>
    </div>
  );
}
