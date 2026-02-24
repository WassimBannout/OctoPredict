import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-GB", {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

export function formatElo(rating: number | null | undefined): string {
  if (rating == null) return "—";
  return Math.round(rating).toString();
}

export function confidenceColor(confidence: string): string {
  if (confidence === "HIGH") return "text-green-400";
  if (confidence === "MEDIUM") return "text-yellow-400";
  return "text-red-400";
}

export function outcomeLabel(outcome: string | null): string {
  if (outcome === "HOME_WIN") return "Home Win";
  if (outcome === "AWAY_WIN") return "Away Win";
  if (outcome === "DRAW") return "Draw";
  return "—";
}

export function leagueName(code: string): string {
  const names: Record<string, string> = {
    PL: "Premier League",
    PD: "La Liga",
    BL1: "Bundesliga",
    SA: "Serie A",
  };
  return names[code] ?? code;
}

export function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}
