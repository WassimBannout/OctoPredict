import { cn } from "@/lib/utils";

interface TeamFormStripProps {
  results: string[];  // e.g. ["W", "W", "D", "L", "W"]
  label?: string;
}

const resultColors: Record<string, string> = {
  W: "bg-green-500",
  D: "bg-yellow-500",
  L: "bg-red-500",
  "?": "bg-slate-600",
};

export function TeamFormStrip({ results, label }: TeamFormStripProps) {
  return (
    <div className="flex items-center gap-1">
      {label && <span className="text-xs text-slate-400 mr-1">{label}</span>}
      {results.map((r, i) => (
        <span
          key={i}
          className={cn("w-5 h-5 rounded-sm text-xs font-bold flex items-center justify-center text-white", resultColors[r] ?? "bg-slate-600")}
        >
          {r}
        </span>
      ))}
    </div>
  );
}
