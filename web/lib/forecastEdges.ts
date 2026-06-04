import { Forecast, Snapshot } from "@/lib/api";

export type EdgeStats = {
  yesBid: number | null;
  yesAsk: number | null;
  yesMid: number | null;
  spread: number | null;
  edgeVsMid: number | null;
  edgeBuyYes: number | null;
  edgeBuyNo: number | null;
  edgeSellYes: number | null;
  edgeSellNo: number | null;
  bestExecutableEdge: number | null;
  spreadPenalty: number | null;
};

export function forecastEdgeStats(forecast: Forecast, snapshot?: Snapshot): EdgeStats {
  const yesBid = snapshot?.yes_bid_bps ?? null;
  const yesAsk = snapshot?.yes_ask_bps ?? null;
  const yesMid = yesBid !== null && yesAsk !== null ? Math.round((yesBid + yesAsk) / 2) : forecast.market_probability_yes_bps;
  const spread = yesBid !== null && yesAsk !== null ? yesAsk - yesBid : null;
  const edgeVsMid = forecast.forecast_probability_yes_bps - yesMid;
  const edgeBuyYes = yesAsk !== null ? forecast.forecast_probability_yes_bps - yesAsk : null;
  const edgeBuyNo = yesBid !== null ? (10000 - forecast.forecast_probability_yes_bps) - (10000 - yesBid) : null;
  const edgeSellYes = yesBid !== null ? yesBid - forecast.forecast_probability_yes_bps : null;
  const edgeSellNo = yesAsk !== null ? forecast.forecast_probability_yes_bps - yesAsk : null;
  const executableEdges = [edgeBuyYes, edgeBuyNo, edgeSellYes, edgeSellNo].filter((value): value is number => value !== null);
  const bestExecutableEdge = executableEdges.length > 0 ? Math.max(...executableEdges) : null;
  const spreadPenalty = bestExecutableEdge !== null ? Math.abs(edgeVsMid) - bestExecutableEdge : null;
  return { yesBid, yesAsk, yesMid, spread, edgeVsMid, edgeBuyYes, edgeBuyNo, edgeSellYes, edgeSellNo, bestExecutableEdge, spreadPenalty };
}
