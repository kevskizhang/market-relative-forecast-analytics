import { apiGet, Market, Position } from "@/lib/api";
import { formatBps, formatDate, formatMoney, formatQuantity } from "@/lib/format";

export default async function NeedsForecastPage() {
  const [positions, markets] = await Promise.all([
    apiGet<Position[]>("/positions"),
    apiGet<Market[]>("/markets"),
  ]);
  const marketById = new Map(markets.map((market) => [market.id, market]));
  const missing = positions.filter((position) => !position.linked_forecast_id);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Needs Forecast</h1>
          <div className="muted">Imported positions that need your probability, thesis, and notes.</div>
        </div>
        <a className="button" href="/settings/kalshi">Sync Kalshi</a>
      </div>
      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>Market</th>
              <th>Opened</th>
              <th>Side</th>
              <th>Qty</th>
              <th>Avg Entry</th>
              <th>Cost Basis</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {missing.map((position) => {
              const market = marketById.get(position.market_id);
              return (
                <tr key={position.id}>
                  <td>{market ? <a href={`/markets/${market.id}`}>{market.title}</a> : position.market_id}</td>
                  <td>{formatDate(position.opened_at)}</td>
                  <td>{position.side}</td>
                  <td>{formatQuantity(position.quantity)}</td>
                  <td>{formatBps(position.average_entry_price_bps)}</td>
                  <td>{formatMoney(position.remaining_cost_basis_minor_units)}</td>
                  <td>{market && <a href={`/markets/${market.id}`}>Add forecast</a>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {missing.length === 0 && <p className="muted">No imported positions are missing forecasts.</p>}
      </section>
    </div>
  );
}
