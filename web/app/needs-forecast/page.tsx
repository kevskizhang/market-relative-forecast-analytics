import { apiGet, Forecast, Market, Position } from "@/lib/api";
import { formatBps, formatDate, formatMoney, formatQuantity, statusClass } from "@/lib/format";
import { LinkForecastForm } from "./LinkForecastForm";

export default async function NeedsForecastPage() {
  const [positions, markets] = await Promise.all([
    apiGet<Position[]>("/positions"),
    apiGet<Market[]>("/markets"),
  ]);
  const marketById = new Map(markets.map((market) => [market.id, market]));
  const missing = positions.filter((position) => !position.linked_forecast_id);
  const marketIds = Array.from(new Set(missing.map((position) => position.market_id)));
  const forecastLists = await Promise.all(
    marketIds.map(async (marketId) => [marketId, await apiGet<Forecast[]>(`/markets/${marketId}/forecasts`)] as const)
  );
  const forecastsByMarketId = new Map(forecastLists);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Missing Forecasts</h1>
          <div className="muted">Imported positions that need your probability, thesis, and notes.</div>
        </div>
        <a className="button" href="/settings/kalshi">Sync Kalshi</a>
      </div>
      <section className="panel">
        <div className="section-head">
          <div>
            <h2>Forecast Queue</h2>
            <div className="muted">{missing.length} imported positions need forecasts.</div>
          </div>
          <span className={missing.length > 0 ? "pill status-missing" : "pill status-resolved"}>{missing.length > 0 ? "action needed" : "clear"}</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Market</th>
                <th>Opened</th>
                <th>Side</th>
                <th>Status</th>
                <th className="numeric">Qty</th>
                <th className="numeric">Avg Entry</th>
                <th className="numeric">Cost Basis</th>
                <th className="numeric">Forecast</th>
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
                    <td><span className={statusClass(position.status)}>{position.status}</span></td>
                    <td className="numeric">{formatQuantity(position.quantity)}</td>
                    <td className="numeric">{formatBps(position.average_entry_price_bps)}</td>
                    <td className="numeric">{formatMoney(position.remaining_cost_basis_minor_units)}</td>
                    <td className="numeric">
                      <LinkForecastForm position={position} forecasts={forecastsByMarketId.get(position.market_id) ?? []} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {missing.length === 0 && <div className="empty">No imported positions are missing forecasts.</div>}
      </section>
    </div>
  );
}
