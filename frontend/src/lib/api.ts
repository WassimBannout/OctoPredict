import type {
  Match,
  Prediction,
  PredictionHistory,
  AccuracyStats,
  Team,
  TeamDetail,
  League,
  ModelStats,
  OverviewStats,
} from "./types";

const BASE = "/api/v1";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, { ...options, cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// Health
export const getHealth = () => fetchJson<{ status: string; version: string }>(`${BASE}/health`);

// Leagues
export const getLeagues = () => fetchJson<League[]>(`${BASE}/leagues`);
export const getStandings = (code: string) =>
  fetchJson<{ league_code: string; standings: unknown[] }>(`${BASE}/leagues/${code}/standings`);

// Matches
export const getUpcomingMatches = (leagueCode?: string, daysAhead = 7) => {
  const params = new URLSearchParams({ days_ahead: String(daysAhead) });
  if (leagueCode) params.set("league_code", leagueCode);
  return fetchJson<Match[]>(`${BASE}/matches/upcoming?${params}`);
};

export const getRecentMatches = (leagueCode?: string, daysBack = 7) => {
  const params = new URLSearchParams({ days_back: String(daysBack) });
  if (leagueCode) params.set("league_code", leagueCode);
  return fetchJson<Match[]>(`${BASE}/matches/recent?${params}`);
};

export const getMatch = (id: number) => fetchJson<Match>(`${BASE}/matches/${id}`);
export const getMatchFeatures = (id: number) =>
  fetchJson<{ match_id: number; features: Record<string, number>; h2h_available: boolean }>(
    `${BASE}/matches/${id}/features`
  );

// Predictions
export const getPredictionHistory = (page = 1, limit = 20, leagueCode?: string) => {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (leagueCode) params.set("league_code", leagueCode);
  return fetchJson<PredictionHistory>(`${BASE}/predictions/history?${params}`);
};

export const getAccuracyStats = (leagueCode?: string, windowDays = 90) => {
  const params = new URLSearchParams({ window_days: String(windowDays) });
  if (leagueCode) params.set("league_code", leagueCode);
  return fetchJson<AccuracyStats>(`${BASE}/predictions/accuracy?${params}`);
};

export const generatePredictions = (forceRefresh = false) =>
  fetchJson<{ generated: number; force_refresh: boolean }>(
    `${BASE}/predictions/generate?force_refresh=${forceRefresh}`,
    { method: "POST" }
  );

// Teams
export const getTeams = (leagueCode?: string) => {
  const params = leagueCode ? `?league_code=${leagueCode}` : "";
  return fetchJson<Team[]>(`${BASE}/teams${params}`);
};

export const getTeam = (id: number) => fetchJson<TeamDetail>(`${BASE}/teams/${id}`);

// Stats
export const getModelStats = () => fetchJson<ModelStats>(`${BASE}/stats/model`);
export const getOverviewStats = () => fetchJson<OverviewStats>(`${BASE}/stats/overview`);
export const triggerSync = () =>
  fetchJson<{ synced: number; results_updated: number; predictions: number; resolved: number }>(
    `${BASE}/admin/sync`,
    { method: "POST" }
  );
