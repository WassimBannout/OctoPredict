"use client";
import Image from "next/image";
import type { StandingRow } from "@/lib/types";

interface StandingsTableProps {
  standings: StandingRow[];
}

export function StandingsTable({ standings }: StandingsTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-slate-400 border-b border-slate-700">
            <th className="text-left pb-2 w-8">#</th>
            <th className="text-left pb-2">Team</th>
            <th className="text-center pb-2">P</th>
            <th className="text-center pb-2">W</th>
            <th className="text-center pb-2">D</th>
            <th className="text-center pb-2">L</th>
            <th className="text-center pb-2">GD</th>
            <th className="text-center pb-2 font-bold text-white">Pts</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((row) => (
            <tr key={row.position} className="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
              <td className="py-2 text-slate-400">{row.position}</td>
              <td className="py-2">
                <div className="flex items-center gap-2">
                  {row.team.crest && (
                    <div className="relative h-5 w-5 flex-shrink-0">
                      <Image src={row.team.crest} alt={row.team.tla} fill className="object-contain" />
                    </div>
                  )}
                  <span className="font-medium">{row.team.shortName}</span>
                </div>
              </td>
              <td className="py-2 text-center text-slate-400">{row.playedGames}</td>
              <td className="py-2 text-center text-green-400">{row.won}</td>
              <td className="py-2 text-center text-yellow-400">{row.draw}</td>
              <td className="py-2 text-center text-red-400">{row.lost}</td>
              <td className="py-2 text-center text-slate-300">
                {row.goalDifference > 0 ? `+${row.goalDifference}` : row.goalDifference}
              </td>
              <td className="py-2 text-center font-bold">{row.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
