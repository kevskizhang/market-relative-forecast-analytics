import { API_URL } from "@/lib/api";

const exports = ["markets", "forecasts", "positions", "executions", "outcomes", "postmortems", "bankroll-snapshots", "kalshi-fills", "kalshi-orders", "kalshi-settlements", "kalshi-position-snapshots", "kalshi-balance-snapshots", "kalshi-deposits", "kalshi-withdrawals"];

export default function ExportPage() {
  return (
    <div className="stack">
      <div>
        <h1>Export</h1>
        <div className="muted">Download CSV files for external analysis.</div>
      </div>
      <section className="panel">
        <div className="grid">
          {exports.map((name) => (
            <a className="button secondary" key={name} href={`${API_URL}/exports/${name}.csv`}>{name}.csv</a>
          ))}
        </div>
      </section>
    </div>
  );
}
