import { KalshiFillsImportForm } from "./KalshiFillsImportForm";
import { apiGet } from "@/lib/api";
import { RebuildKalshiButton } from "./RebuildKalshiButton";

type Reconciliation = {
  raw_fills: number;
  unconverted_fills: number;
  raw_orders: number;
  raw_settlements: number;
  unconverted_settlements: number;
  raw_position_snapshots: number;
  raw_balance_snapshots: number;
  raw_deposits: number;
  raw_withdrawals: number;
  imported_positions_missing_forecast: number;
  imported_open_positions: number;
  resolved_markets_needing_review: number;
};

export default async function KalshiSettingsPage() {
  const reconciliation = await apiGet<Reconciliation>("/kalshi/reconciliation").catch(() => null);
  return (
    <div className="stack">
      <div>
        <h1>Kalshi</h1>
        <div className="muted">Read-only authenticated fill import.</div>
      </div>
      <KalshiFillsImportForm />
      <section className="panel">
        <h2>Repair Imported State</h2>
        <p className="muted">Use this after sync logic changes or if imported positions look stale. Raw Kalshi records remain the source of truth.</p>
        <RebuildKalshiButton />
      </section>
      {reconciliation && (
        <section className="panel">
          <h2>Reconciliation</h2>
          <div className="grid">
            <div><div className="metric">{reconciliation.raw_fills}</div><div className="muted">raw fills</div></div>
            <div><div className="metric">{reconciliation.unconverted_fills}</div><div className="muted">unconverted fills</div></div>
            <div><div className="metric">{reconciliation.raw_orders}</div><div className="muted">raw orders</div></div>
            <div><div className="metric">{reconciliation.raw_settlements}</div><div className="muted">raw settlements</div></div>
            <div><div className="metric">{reconciliation.unconverted_settlements}</div><div className="muted">unconverted settlements</div></div>
            <div><div className="metric">{reconciliation.raw_balance_snapshots}</div><div className="muted">balance snapshots</div></div>
            <div><div className="metric">{reconciliation.raw_deposits}</div><div className="muted">deposits</div></div>
            <div><div className="metric">{reconciliation.raw_withdrawals}</div><div className="muted">withdrawals</div></div>
            <div><div className="metric">{reconciliation.imported_positions_missing_forecast}</div><div className="muted">positions missing forecasts</div></div>
          </div>
        </section>
      )}
      <section className="panel">
        <h2>How It Works</h2>
        <p>Sync stores raw Kalshi fills, orders, settlements, and position snapshots before conversion. Fills become executions; settlements become outcomes.</p>
        <p>Forecasts are still manual. After importing positions, attach or create the forecast that justified each trade.</p>
      </section>
    </div>
  );
}
