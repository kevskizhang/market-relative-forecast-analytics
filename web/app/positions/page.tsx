import { apiGet, Position } from "@/lib/api";
import { formatBps, formatDate, formatMoney } from "@/lib/format";

export default async function PositionsPage() {
  const positions = await apiGet<Position[]>("/positions");
  return (
    <div className="stack">
      <div>
        <h1>Positions</h1>
        <div className="muted">Open, closed, and resolved exposure.</div>
      </div>
      <section className="panel">
        <table>
          <thead><tr><th>Opened</th><th>Side</th><th>Status</th><th>Qty</th><th>Avg Entry</th><th>Cost Basis</th><th>P&amp;L</th></tr></thead>
          <tbody>
            {positions.map((position) => (
              <tr key={position.id}>
                <td><a href={`/positions/${position.id}`}>{formatDate(position.opened_at)}</a></td>
                <td>{position.side}</td>
                <td>{position.status}</td>
                <td>{position.quantity}</td>
                <td>{formatBps(position.average_entry_price_bps)}</td>
                <td>{formatMoney(position.remaining_cost_basis_minor_units)}</td>
                <td>{formatMoney(position.total_pnl_minor_units ?? position.realized_pnl_minor_units)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

