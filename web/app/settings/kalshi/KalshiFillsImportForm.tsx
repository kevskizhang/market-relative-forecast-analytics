"use client";

import { API_URL } from "@/lib/api";
import { useState, FormEvent } from "react";

type ImportResult = {
  fills_received: number;
  fills_stored: number;
  fills_converted: number;
  fills_skipped: number;
  orders_received: number;
  orders_stored: number;
  orders_skipped: number;
  settlements_received: number;
  settlements_stored: number;
  settlements_converted: number;
  settlements_skipped: number;
  position_snapshots_received: number;
  position_snapshots_stored: number;
  position_snapshots_skipped: number;
  balance_snapshots_stored: number;
  deposits_received: number;
  deposits_stored: number;
  deposits_skipped: number;
  withdrawals_received: number;
  withdrawals_stored: number;
  withdrawals_skipped: number;
};

export function KalshiFillsImportForm() {
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const ticker = String(form.get("ticker") || "").trim();
    setResult(null);
    setError(null);
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/kalshi/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: ticker || null, include_historical: form.get("include_historical") === "on" }),
      });
      if (!response.ok) {
        setError(await response.text());
        return;
      }
      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Sync Kalshi Activity</h2>
      <form className="form" onSubmit={submit}>
        <label>Optional Ticker<input name="ticker" placeholder="Leave blank for recent fills" /></label>
        <label style={{ display: "flex", gridTemplateColumns: "auto 1fr", alignItems: "center" }}>
          <input name="include_historical" type="checkbox" style={{ width: "auto" }} />
          Include historical fills
        </label>
        {error && <div className="error">{error}</div>}
        {result && (
          <div className="grid">
            <div className="panel"><h3>Fills</h3><p>Received {result.fills_received}</p><p>Stored {result.fills_stored}</p><p>Converted {result.fills_converted}</p><p>Skipped {result.fills_skipped}</p></div>
            <div className="panel"><h3>Orders</h3><p>Received {result.orders_received}</p><p>Stored {result.orders_stored}</p><p>Skipped {result.orders_skipped}</p></div>
            <div className="panel"><h3>Settlements</h3><p>Received {result.settlements_received}</p><p>Stored {result.settlements_stored}</p><p>Converted {result.settlements_converted}</p><p>Skipped {result.settlements_skipped}</p></div>
            <div className="panel"><h3>Positions</h3><p>Received {result.position_snapshots_received}</p><p>Stored {result.position_snapshots_stored}</p><p>Skipped {result.position_snapshots_skipped}</p></div>
            <div className="panel"><h3>Account</h3><p>Balance snapshots {result.balance_snapshots_stored}</p><p>Deposits stored {result.deposits_stored}</p><p>Withdrawals stored {result.withdrawals_stored}</p></div>
          </div>
        )}
        <button disabled={loading}>{loading ? "Syncing..." : "Sync Kalshi"}</button>
      </form>
    </section>
  );
}
