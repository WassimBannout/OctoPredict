"use client";
import { pct, cn } from "@/lib/utils";

interface PredictionBarProps {
  probHome: number;
  probDraw: number;
  probAway: number;
  predictedOutcome: string;
  actualOutcome?: string | null;
}

export function PredictionBar({
  probHome,
  probDraw,
  probAway,
  predictedOutcome,
  actualOutcome,
}: PredictionBarProps) {
  const isResolved = actualOutcome != null;

  const homeCorrect = isResolved && actualOutcome === "HOME_WIN";
  const drawCorrect = isResolved && actualOutcome === "DRAW";
  const awayCorrect = isResolved && actualOutcome === "AWAY_WIN";

  return (
    <div>
      {/* Probability bar */}
      <div className="flex h-2 rounded-full overflow-hidden w-full">
        <div
          className={cn("transition-all", homeCorrect ? "bg-green-500" : predictedOutcome === "HOME_WIN" ? "bg-blue-500" : "bg-slate-600")}
          style={{ width: pct(probHome) }}
        />
        <div
          className={cn("transition-all", drawCorrect ? "bg-green-500" : predictedOutcome === "DRAW" ? "bg-yellow-500" : "bg-slate-700")}
          style={{ width: pct(probDraw) }}
        />
        <div
          className={cn("transition-all", awayCorrect ? "bg-green-500" : predictedOutcome === "AWAY_WIN" ? "bg-purple-500" : "bg-slate-600")}
          style={{ width: pct(probAway) }}
        />
      </div>

      {/* Probability labels */}
      <div className="flex justify-between text-xs mt-1 text-slate-400">
        <span className={cn(predictedOutcome === "HOME_WIN" && "text-blue-300 font-semibold")}>
          {pct(probHome)} Home
        </span>
        <span className={cn(predictedOutcome === "DRAW" && "text-yellow-300 font-semibold")}>
          {pct(probDraw)} Draw
        </span>
        <span className={cn(predictedOutcome === "AWAY_WIN" && "text-purple-300 font-semibold")}>
          {pct(probAway)} Away
        </span>
      </div>
    </div>
  );
}
