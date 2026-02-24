"use client";
import useSWR from "swr";
import { getLeagues, getStandings, getOverviewStats, getModelStats } from "@/lib/api";

export function useLeagues() {
  return useSWR("leagues", getLeagues, { refreshInterval: 10 * 60 * 1000 });
}

export function useStandings(code: string) {
  return useSWR(["standings", code], () => getStandings(code), {
    refreshInterval: 10 * 60 * 1000,
  });
}

export function useOverviewStats() {
  return useSWR("overview-stats", getOverviewStats, { refreshInterval: 60 * 1000 });
}

export function useModelStats() {
  return useSWR("model-stats", getModelStats, { refreshInterval: 5 * 60 * 1000 });
}
