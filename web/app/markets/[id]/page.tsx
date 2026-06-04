import { apiGet, Forecast, Market, Position, Snapshot } from "@/lib/api";
import { formatBps, formatDate, formatMoney, formatQuantity, pnlClass, signedBpsClass, statusClass } from "@/lib/format";
import { MarketActions } from "./MarketActions";
import { UndoResolutionButton } from "./UndoResolutionButton";

type EdgeStats = {
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

function forecastEdgeStats(forecast: Forecast, snapshotsById: Map<string, Snapshot>): EdgeStats {
  const snapshot = forecast.market_snapshot_id ? snapshotsById.get(forecast.market_snapshot_id) : undefined;
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

export default async function MarketDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [market, snapshots, forecasts, positions, scores] = await Promise.all([
    apiGet<Market>(`/markets/${id}`),
    apiGet<Snapshot[]>(`/markets/${id}/snapshots`),
    apiGet<Forecast[]>(`/markets/${id}/forecasts`),
    apiGet<Position[]>(`/markets/${id}/positions`),
    apiGet<Array<{ forecast_id: string; brier_user_bps_squared: number; brier_improvement_bps_squared: number }>>(`/markets/${id}/scores`),
  ]);
  const snapshotsById = new Map(snapshots.map((snapshot) => [snapshot.id, snapshot]));

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>{market.title}</h1>
          <div className="muted">{market.category} | expected resolution {market.expected_resolution_date}</div>
        </div>
        <div className="page-actions">
          <a className="button secondary" href={`/markets/${market.id}/edit`}>Edit</a>
          <span className={statusClass(market.status)}>{market.status}</span>
        </div>
      </div>

      <section className="panel">
        <div className="section-head">
          <div>
            <h2>Market</h2>
            <div className="muted">{market.platform_market_id ?? "Manual market"}</div>
          </div>
          {market.final_outcome && <span className={statusClass("resolved")}>Outcome {market.final_outcome}</span>}
        </div>
        <p>{market.resolution_criteria}</p>
        {market.market_url && <p><a href={market.market_url} target="_blank">Open Kalshi market</a></p>}
        {market.status !== "open" && <UndoResolutionButton marketId={market.id} />}
      </section>

      <section className="panel">
          <h2>Forecasts</h2>
          <div className="table-wrap">
            <table className="table-compact">
            <thead><tr><th className="nowrap">Time</th><th className="numeric">Bid</th><th className="numeric">Ask</th><th className="numeric">Mid</th><th className="numeric">Spr</th><th className="numeric">Mine</th><th className="numeric">vs Mid</th><th className="numeric">Buy Y</th><th className="numeric">Buy N</th><th className="numeric">Sell Y</th><th className="numeric">Sell N</th><th className="numeric">Best</th><th className="numeric">Penalty</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {forecasts.map((forecast) => {
                  const stats = forecastEdgeStats(forecast, snapshotsById);
                  return (
                    <tr key={forecast.id}>
                      <td>{formatDate(forecast.timestamp)}</td>
                      <td className="numeric">{formatBps(stats.yesBid)}</td>
                      <td className="numeric">{formatBps(stats.yesAsk)}</td>
                      <td className="numeric">{formatBps(stats.yesMid)}</td>
                      <td className="numeric">{formatBps(stats.spread)}</td>
                      <td className="numeric">{formatBps(forecast.forecast_probability_yes_bps)}</td>
                      <td className={signedBpsClass(stats.edgeVsMid)}>{formatBps(stats.edgeVsMid)}</td>
                      <td className={signedBpsClass(stats.edgeBuyYes)}>{formatBps(stats.edgeBuyYes)}</td>
                      <td className={signedBpsClass(stats.edgeBuyNo)}>{formatBps(stats.edgeBuyNo)}</td>
                      <td className={signedBpsClass(stats.edgeSellYes)}>{formatBps(stats.edgeSellYes)}</td>
                      <td className={signedBpsClass(stats.edgeSellNo)}>{formatBps(stats.edgeSellNo)}</td>
                      <td className={signedBpsClass(stats.bestExecutableEdge)}>{formatBps(stats.bestExecutableEdge)}</td>
                      <td className={signedBpsClass(stats.spreadPenalty !== null ? -stats.spreadPenalty : null)}>{formatBps(stats.spreadPenalty)}</td>
                      <td><span className={statusClass(forecast.status)}>{forecast.status}</span></td>
                      <td><a href={`/forecasts/${forecast.id}/edit`}>Edit</a></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="muted table-note">
            Buy YES uses YES ask; Buy NO uses NO ask implied by YES bid. Sell YES uses YES bid; Sell NO uses NO bid implied by YES ask. Best Edge is the best executable action. Spread Penalty is the edge lost from mid to execution.
          </div>
          {forecasts.length === 0 && <div className="empty">No forecasts logged for this market.</div>}
        </section>

      <div className="grid">
        <section className="panel">
          <h2>Snapshots</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Time</th><th className="numeric">YES %</th><th className="numeric">Bid</th><th className="numeric">Ask</th></tr></thead>
              <tbody>
                {snapshots.map((snapshot) => (
                  <tr key={snapshot.id}>
                    <td>{formatDate(snapshot.timestamp)}</td>
                    <td className="numeric">{formatBps(snapshot.market_probability_yes_bps)}</td>
                    <td className="numeric">{formatBps(snapshot.yes_bid_bps)}</td>
                    <td className="numeric">{formatBps(snapshot.yes_ask_bps)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {snapshots.length === 0 && <div className="empty">No market snapshots yet.</div>}
        </section>
      </div>

      <section className="panel">
        <h2>Positions</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Opened</th><th>Side</th><th>Status</th><th className="numeric">Qty</th><th className="numeric">Cost Basis</th><th className="numeric">Realized P&amp;L</th><th></th></tr></thead>
            <tbody>
              {positions.map((position) => (
                <tr key={position.id}>
                  <td><a href={`/positions/${position.id}`}>{formatDate(position.opened_at)}</a></td>
                  <td>{position.side}</td>
                  <td><span className={statusClass(position.status)}>{position.status}</span></td>
                  <td className="numeric">{formatQuantity(position.quantity)}</td>
                  <td className="numeric">{formatMoney(position.remaining_cost_basis_minor_units)}</td>
                  <td className={`numeric ${pnlClass(position.realized_pnl_minor_units)}`}>{formatMoney(position.realized_pnl_minor_units)}</td>
                  <td><a href={`/positions/${position.id}/edit`}>Edit</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {positions.length === 0 && <div className="empty">No positions for this market.</div>}
      </section>

      {scores.length > 0 && (
        <section className="panel">
          <h2>Scores</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Forecast</th><th className="numeric">Brier</th><th className="numeric">Improvement</th></tr></thead>
              <tbody>
                {scores.map((score) => (
                  <tr key={score.forecast_id}>
                    <td>{score.forecast_id.slice(0, 8)}</td>
                    <td className="numeric">{(score.brier_user_bps_squared / 100000000).toFixed(4)}</td>
                    <td className={score.brier_improvement_bps_squared >= 0 ? "numeric positive" : "numeric negative"}>{(score.brier_improvement_bps_squared / 100000000).toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <MarketActions marketId={id} kalshiTicker={market.platform_market_id} forecasts={forecasts} positions={positions} />
    </div>
  );
}
