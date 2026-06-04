import { apiGet, Forecast, Market, Position, Snapshot } from "@/lib/api";
import { formatBps, formatDate, formatMoney } from "@/lib/format";
import { MarketActions } from "./MarketActions";

export default async function MarketDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [market, snapshots, forecasts, positions, scores] = await Promise.all([
    apiGet<Market>(`/markets/${id}`),
    apiGet<Snapshot[]>(`/markets/${id}/snapshots`),
    apiGet<Forecast[]>(`/markets/${id}/forecasts`),
    apiGet<Position[]>(`/markets/${id}/positions`),
    apiGet<Array<{ forecast_id: string; brier_user_bps_squared: number; brier_improvement_bps_squared: number }>>(`/markets/${id}/scores`),
  ]);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>{market.title}</h1>
          <div className="muted">{market.category} | expected resolution {market.expected_resolution_date}</div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <a className="button secondary" href={`/markets/${market.id}/edit`}>Edit</a>
          <span className="pill">{market.status}</span>
        </div>
      </div>

      <section className="panel">
        <h2>Market</h2>
        <p>{market.resolution_criteria}</p>
        {market.market_url && <p><a href={market.market_url} target="_blank">Open Kalshi market</a></p>}
      </section>

      <div className="grid">
        <section className="panel">
          <h2>Forecasts</h2>
          <table>
            <thead><tr><th>Time</th><th>Market</th><th>Mine</th><th>Edge</th><th>Status</th></tr></thead>
            <tbody>
              {forecasts.map((forecast) => (
                <tr key={forecast.id}>
                  <td>{formatDate(forecast.timestamp)}</td>
                  <td>{formatBps(forecast.market_probability_yes_bps)}</td>
                  <td>{formatBps(forecast.forecast_probability_yes_bps)}</td>
                  <td>{formatBps(forecast.edge_bps)}</td>
                  <td>{forecast.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="panel">
          <h2>Snapshots</h2>
          <table>
            <thead><tr><th>Time</th><th>YES %</th><th>Bid</th><th>Ask</th></tr></thead>
            <tbody>
              {snapshots.map((snapshot) => (
                <tr key={snapshot.id}>
                  <td>{formatDate(snapshot.timestamp)}</td>
                  <td>{formatBps(snapshot.market_probability_yes_bps)}</td>
                  <td>{formatBps(snapshot.yes_bid_bps)}</td>
                  <td>{formatBps(snapshot.yes_ask_bps)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <section className="panel">
        <h2>Positions</h2>
        <table>
          <thead><tr><th>Opened</th><th>Side</th><th>Status</th><th>Qty</th><th>Cost Basis</th><th>Realized P&amp;L</th></tr></thead>
          <tbody>
            {positions.map((position) => (
              <tr key={position.id}>
                <td><a href={`/positions/${position.id}`}>{formatDate(position.opened_at)}</a></td>
                <td>{position.side}</td>
                <td>{position.status}</td>
                <td>{position.quantity}</td>
                <td>{formatMoney(position.remaining_cost_basis_minor_units)}</td>
                <td>{formatMoney(position.realized_pnl_minor_units)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {scores.length > 0 && (
        <section className="panel">
          <h2>Scores</h2>
          <table>
            <thead><tr><th>Forecast</th><th>Brier</th><th>Improvement</th></tr></thead>
            <tbody>
              {scores.map((score) => (
                <tr key={score.forecast_id}>
                  <td>{score.forecast_id.slice(0, 8)}</td>
                  <td>{(score.brier_user_bps_squared / 100000000).toFixed(4)}</td>
                  <td>{(score.brier_improvement_bps_squared / 100000000).toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <MarketActions marketId={id} forecasts={forecasts} positions={positions} />
    </div>
  );
}
