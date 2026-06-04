import { apiGet } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import { BankrollForm } from "./BankrollForm";

type Snapshot = {
  id: string;
  timestamp: string;
  cash_balance_minor_units: number;
  open_position_value_minor_units: number;
  total_equity_minor_units: number;
  notes?: string | null;
};

export default async function BankrollPage() {
  const snapshots = await apiGet<Snapshot[]>("/bankroll-snapshots");
  return (
    <div className="stack">
      <div>
        <h1>Bankroll</h1>
        <div className="muted">Manual account equity snapshots.</div>
      </div>
      <BankrollForm />
      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Time</th><th className="numeric">Cash</th><th className="numeric">Open Value</th><th className="numeric">Total Equity</th><th>Notes</th></tr></thead>
            <tbody>
              {snapshots.map((snapshot) => (
                <tr key={snapshot.id}>
                  <td>{formatDate(snapshot.timestamp)}</td>
                  <td className="numeric">{formatMoney(snapshot.cash_balance_minor_units)}</td>
                  <td className="numeric">{formatMoney(snapshot.open_position_value_minor_units)}</td>
                  <td className="numeric">{formatMoney(snapshot.total_equity_minor_units)}</td>
                  <td>{snapshot.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {snapshots.length === 0 && <div className="empty">No manual bankroll snapshots yet.</div>}
      </section>
    </div>
  );
}
