"use client";
import useSWR from "swr";
import { getPredictionHistory, getAccuracyStats } from "@/lib/api";

export function usePredictionHistory(page = 1, limit = 20, leagueCode?: string) {
  return useSWR(
    ["prediction-history", page, limit, leagueCode],
    () => getPredictionHistory(page, limit, leagueCode),
    { refreshInterval: 60 * 1000 }
  );
}

export function useAccuracyStats(leagueCode?: string, windowDays = 90) {
  return useSWR(
    ["accuracy-stats", leagueCode, windowDays],
    () => getAccuracyStats(leagueCode, windowDays),
    { refreshInterval: 5 * 60 * 1000 }
  );
}
