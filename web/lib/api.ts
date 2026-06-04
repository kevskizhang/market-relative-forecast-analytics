export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Market = {
  id: string;
  title: string;
  platform: string;
  platform_market_id?: string | null;
  market_url?: string | null;
  category: string;
  description?: string | null;
  sub_category?: string | null;
  resolution_criteria: string;
  yes_contract_name?: string | null;
  no_contract_name?: string | null;
  expected_resolution_date: string;
  status: string;
  final_outcome?: string | null;
  notes?: string | null;
};

export type Forecast = {
  id: string;
  market_id: string;
  timestamp: string;
  forecast_probability_yes_bps: number;
  market_probability_yes_bps: number;
  edge_bps: number;
  confidence: number;
  thesis: string;
  invalidation_criteria?: string | null;
  research_quality?: string | null;
  forecast_type: string;
  notes?: string | null;
  status: string;
};

export type Snapshot = {
  id: string;
  market_id: string;
  timestamp: string;
  market_probability_yes_bps: number;
  yes_bid_bps?: number | null;
  yes_ask_bps?: number | null;
  spread_bps?: number | null;
};

export type KalshiMarket = {
  ticker: string;
  title: string;
  category: string;
  market_url: string;
  resolution_criteria: string;
  expected_resolution_date?: string | null;
  yes_bid_bps?: number | null;
  yes_ask_bps?: number | null;
  last_trade_price_bps?: number | null;
  market_probability_yes_bps?: number | null;
  volume?: number | null;
  open_interest?: number | null;
};

export type Position = {
  id: string;
  market_id: string;
  linked_forecast_id?: string | null;
  side: "YES" | "NO";
  status: string;
  opened_at: string;
  closed_at?: string | null;
  quantity: number;
  average_entry_price_bps?: number | null;
  average_exit_price_bps?: number | null;
  initial_cost_minor_units?: number | null;
  remaining_cost_basis_minor_units?: number | null;
  realized_pnl_minor_units: number;
  total_pnl_minor_units?: number | null;
  fees_minor_units: number;
  position_notes?: string | null;
};

export type Execution = {
  id: string;
  position_id: string;
  market_id: string;
  timestamp: string;
  action: "buy" | "sell";
  side: "YES" | "NO";
  price_bps: number;
  quantity: number;
  fees_minor_units: number;
  reason?: string | null;
};

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API GET ${path} failed: ${response.status}`);
  }
  return response.json();
}
