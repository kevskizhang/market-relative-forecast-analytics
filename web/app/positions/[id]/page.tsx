import { apiGet, Execution, Forecast, Position } from "@/lib/api";
import { formatBps, formatDate, formatMoney, formatQuantity } from "@/lib/format";
import { ExecutionForm } from "./ExecutionForm";

export default async function PositionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const position = await apiGet<Position>(`/positions/${id}`);
  const [executions, forecasts] = await Promise.all([
    apiGet<Execution[]>(`/positions/${id}/executions`),
    apiGet<Forecast[]>(`/markets/${position.market_id}/forecasts`),
  ]);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>{position.side} Position</h1>
          <div className="muted">Opened {formatDate(position.opened_at)}</div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <a className="button secondary" href={`/positions/${position.id}/edit`}>Edit</a>
          <span className="pill">{position.status}</span>
        </div>
      </div>

      <div className="grid">
        <section className="panel"><h2>Quantity</h2><div className="metric">{formatQuantity(position.quantity)}</div></section>
        <section className="panel"><h2>Avg Entry</h2><div className="metric">{formatBps(position.average_entry_price_bps)}</div></section>
        <section className="panel"><h2>Cost Basis</h2><div className="metric">{formatMoney(position.remaining_cost_basis_minor_units)}</div></section>
        <section className="panel"><h2>Realized P&amp;L</h2><div className="metric">{formatMoney(position.realized_pnl_minor_units)}</div></section>
      </div>

      <section className="panel">
        <h2>Executions</h2>
        <table>
          <thead><tr><th>Time</th><th>Action</th><th>Side</th><th>Price</th><th>Qty</th><th>Fees</th><th>Reason</th></tr></thead>
          <tbody>
            {executions.map((execution) => (
              <tr key={execution.id}>
                <td>{formatDate(execution.timestamp)}</td>
                <td>{execution.action}</td>
                <td>{execution.side}</td>
                <td>{formatBps(execution.price_bps)}</td>
                <td>{formatQuantity(execution.quantity)}</td>
                <td>{formatMoney(execution.fees_minor_units)}</td>
                <td>{execution.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <ExecutionForm position={position} forecasts={forecasts} />
    </div>
  );
}
