"use client";
import useSWR from "swr";
import { getUpcomingMatches, getRecentMatches } from "@/lib/api";

export function useUpcomingMatches(leagueCode?: string, daysAhead = 7) {
  return useSWR(
    ["upcoming-matches", leagueCode, daysAhead],
    () => getUpcomingMatches(leagueCode, daysAhead),
    { refreshInterval: 5 * 60 * 1000 }
  );
}

export function useRecentMatches(leagueCode?: string, daysBack = 7) {
  return useSWR(
    ["recent-matches", leagueCode, daysBack],
    () => getRecentMatches(leagueCode, daysBack),
    { refreshInterval: 5 * 60 * 1000 }
  );
}
