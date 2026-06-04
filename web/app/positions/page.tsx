import { apiGet, Market, Position } from "@/lib/api";
import { formatBps, formatDate, formatMoney, formatQuantity, pnlClass, statusClass } from "@/lib/format";

export default async function PositionsPage() {
  const [positions, markets] = await Promise.all([
    apiGet<Position[]>("/positions"),
    apiGet<Market[]>("/markets"),
  ]);
  const marketById = new Map(markets.map((market) => [market.id, market]));
  return (
    <div className="stack">
      <div>
        <h1>Positions</h1>
        <div className="muted">Open, closed, and resolved exposure.</div>
      </div>
      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Market</th><th>Opened</th><th>Side</th><th>Status</th><th className="numeric">Qty</th><th className="numeric">Avg Entry</th><th className="numeric">Cost Basis</th><th className="numeric">P&amp;L</th></tr></thead>
            <tbody>
              {positions.map((position) => {
                const pnl = position.total_pnl_minor_units ?? position.realized_pnl_minor_units;
                const market = marketById.get(position.market_id);
                return (
                  <tr key={position.id}>
                    <td>{market ? <a href={`/markets/${market.id}`}>{market.title}</a> : position.market_id}</td>
                    <td><a href={`/positions/${position.id}`}>{formatDate(position.opened_at)}</a></td>
                    <td>{position.side}</td>
                    <td><span className={statusClass(position.status)}>{position.status}</span></td>
                    <td className="numeric">{formatQuantity(position.quantity)}</td>
                    <td className="numeric">{formatBps(position.average_entry_price_bps)}</td>
                    <td className="numeric">{formatMoney(position.remaining_cost_basis_minor_units)}</td>
                    <td className={`numeric ${pnlClass(pnl)}`}>{formatMoney(pnl)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {positions.length === 0 && <div className="empty">No positions imported yet.</div>}
      </section>
    </div>
  );
}
