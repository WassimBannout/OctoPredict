export interface Team {
  id: number;
  external_id: number;
  name: string;
  short_name: string;
  tla: string;
  crest_url: string | null;
  competition_code: string;
  current_elo?: number | null;
}

export interface TeamDetail extends Team {
  elo_history: EloPoint[];
  home_record: Record<string, number>;
  away_record: Record<string, number>;
  last_5_matches: RecentMatch[];
}

export interface EloPoint {
  date: string;
  rating: number;
  change: number;
}

export interface RecentMatch {
  match_id: number;
  date: string;
  result: "W" | "D" | "L" | "?";
}

export interface PredictionSummary {
  prob_home_win: number;
  prob_draw: number;
  prob_away_win: number;
  predicted_outcome: string;
  confidence: "LOW" | "MEDIUM" | "HIGH";
  model_version: string;
}

export interface Match {
  id: number;
  external_id: number;
  competition_code: string;
  season: string;
  matchday: number | null;
  utc_date: string;
  status: string;
  home_team: Team;
  away_team: Team;
  home_score: number | null;
  away_score: number | null;
  outcome: string | null;
  home_position: number | null;
  away_position: number | null;
  prediction?: PredictionSummary | null;
  home_elo?: number | null;
  away_elo?: number | null;
}

export interface Prediction {
  id: number;
  match_id: number;
  prob_home_win: number;
  prob_draw: number;
  prob_away_win: number;
  predicted_outcome: string;
  confidence: string;
  features_snapshot: Record<string, number> | null;
  actual_outcome: string | null;
  is_correct: boolean | null;
  brier_score: number | null;
  rps_score: number | null;
  model_version: string;
  predicted_at: string;
  match?: Match | null;
}

export interface PredictionHistory {
  items: Prediction[];
  total: number;
  page: number;
  limit: number;
}

export interface AccuracyStats {
  total_predictions: number;
  resolved_predictions: number;
  correct_predictions: number;
  accuracy: number;
  display_accuracy: number | null;
  accuracy_source: "resolved_predictions" | "model_validation" | "none";
  avg_brier_score: number | null;
  avg_rps_score: number | null;
  validation_accuracy: number | null;
  validation_brier_score: number | null;
  validation_rps_score: number | null;
  validation_samples: number | null;
  league_code: string | null;
  window_days: number;
}

export interface League {
  code: string;
  name: string;
  team_count: number;
  match_count: number;
}

export interface StandingRow {
  position: number;
  team: { id: number; name: string; shortName: string; tla: string; crest: string };
  playedGames: number;
  won: number;
  draw: number;
  lost: number;
  points: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
}

export interface ModelStats {
  version: string;
  model_type: string;
  created_at: string | null;
  metrics: Record<string, number>;
  feature_importances: Record<string, number>;
  feature_names: string[];
}

export interface OverviewStats {
  total_matches: number;
  finished_matches: number;
  upcoming_matches: number;
  total_predictions: number;
  resolved_predictions: number;
  overall_accuracy: number | null;
  leagues: string[];
  last_sync: string | null;
}
