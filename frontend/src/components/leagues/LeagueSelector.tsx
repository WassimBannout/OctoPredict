"use client";
import { leagueName } from "@/lib/utils";
import { cn } from "@/lib/utils";

const LEAGUES = ["PL", "PD", "BL1", "SA"];

interface LeagueSelectorProps {
  selected: string | undefined;
  onChange: (code: string | undefined) => void;
}

export function LeagueSelector({ selected, onChange }: LeagueSelectorProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        onClick={() => onChange(undefined)}
        className={cn(
          "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
          selected === undefined
            ? "bg-blue-600 text-white"
            : "bg-slate-800 text-slate-300 hover:bg-slate-700"
        )}
      >
        All
      </button>
      {LEAGUES.map((code) => (
        <button
          key={code}
          onClick={() => onChange(code)}
          className={cn(
            "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
            selected === code
              ? "bg-blue-600 text-white"
              : "bg-slate-800 text-slate-300 hover:bg-slate-700"
          )}
        >
          {leagueName(code)}
        </button>
      ))}
    </div>
  );
}
