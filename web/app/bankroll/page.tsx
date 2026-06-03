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
        <table>
          <thead><tr><th>Time</th><th>Cash</th><th>Open Value</th><th>Total Equity</th><th>Notes</th></tr></thead>
          <tbody>
            {snapshots.map((snapshot) => (
              <tr key={snapshot.id}>
                <td>{formatDate(snapshot.timestamp)}</td>
                <td>{formatMoney(snapshot.cash_balance_minor_units)}</td>
                <td>{formatMoney(snapshot.open_position_value_minor_units)}</td>
                <td>{formatMoney(snapshot.total_equity_minor_units)}</td>
                <td>{snapshot.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

