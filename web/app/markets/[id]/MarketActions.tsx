"use client";

import { API_URL, Forecast, Position } from "@/lib/api";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

function pctToBps(value: FormDataEntryValue | null): number {
  return Math.round(Number(value) * 100);
}

function dollarsToCents(value: FormDataEntryValue | null): number {
  return Math.round(Number(value || 0) * 100);
}

async function post(path: string, payload: unknown) {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export function MarketActions({
  marketId,
  forecasts,
  positions,
}: {
  marketId: string;
  forecasts: Forecast[];
  positions: Position[];
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function handle(form: HTMLFormElement, fn: (form: FormData) => Promise<void>) {
    setError(null);
    try {
      await fn(new FormData(form));
      form.reset();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    }
  }

  async function addSnapshotForecast(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    await handle(formElement, async (form) => {
      const marketBps = pctToBps(form.get("market_probability_yes_pct"));
      const snapshot = await post(`/markets/${marketId}/snapshots`, {
        market_probability_yes_bps: marketBps,
        yes_bid_bps: form.get("yes_bid_pct") ? pctToBps(form.get("yes_bid_pct")) : null,
        yes_ask_bps: form.get("yes_ask_pct") ? pctToBps(form.get("yes_ask_pct")) : null,
        last_trade_price_bps: form.get("last_trade_price_pct") ? pctToBps(form.get("last_trade_price_pct")) : null,
      });
      await post(`/markets/${marketId}/forecasts`, {
        market_snapshot_id: snapshot.id,
        market_probability_yes_bps: marketBps,
        forecast_probability_yes_bps: pctToBps(form.get("forecast_probability_yes_pct")),
        confidence: Number(form.get("confidence")),
        thesis: form.get("thesis"),
        invalidation_criteria: form.get("invalidation_criteria"),
        research_quality: form.get("research_quality") || null,
        forecast_type: form.get("forecast_type"),
        notes: form.get("notes"),
      });
    });
  }

  async function openPosition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    await handle(formElement, async (form) => {
      await post("/positions", {
        market_id: marketId,
        linked_forecast_id: form.get("linked_forecast_id"),
        side: form.get("side"),
        entry_price_bps: pctToBps(form.get("entry_price_pct")),
        quantity: Number(form.get("quantity")),
        fees_minor_units: dollarsToCents(form.get("fees")),
        order_type: "manual",
        reason: form.get("reason"),
        notes: form.get("notes"),
      });
    });
  }

  async function resolveMarket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    await handle(formElement, async (form) => {
      await post(`/markets/${marketId}/resolve`, {
        final_outcome: form.get("final_outcome"),
        resolution_notes: form.get("resolution_notes"),
      });
    });
  }

  return (
    <div className="stack">
      {error && <div className="panel error">{error}</div>}

      <section className="panel">
        <h2>Add Snapshot and Forecast</h2>
        <form className="form" onSubmit={addSnapshotForecast}>
          <div className="form-grid">
            <label>Market YES %<input name="market_probability_yes_pct" type="number" step="0.01" min="0" max="100" required /></label>
            <label>Your YES %<input name="forecast_probability_yes_pct" type="number" step="0.01" min="0" max="100" required /></label>
            <label>Confidence<select name="confidence" defaultValue="3"><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
          </div>
          <div className="form-grid">
            <label>YES Bid %<input name="yes_bid_pct" type="number" step="0.01" min="0" max="100" /></label>
            <label>YES Ask %<input name="yes_ask_pct" type="number" step="0.01" min="0" max="100" /></label>
            <label>Last Trade %<input name="last_trade_price_pct" type="number" step="0.01" min="0" max="100" /></label>
          </div>
          <div className="form-grid">
            <label>Research Quality<select name="research_quality" defaultValue="medium"><option value="">-</option><option>low</option><option>medium</option><option>high</option></select></label>
            <label>Forecast Type<select name="forecast_type" defaultValue="initial"><option>initial</option><option>update</option><option>pre_trade</option><option>post_news</option><option>pre_resolution</option></select></label>
          </div>
          <label>Thesis<textarea name="thesis" required /></label>
          <label>Invalidation Criteria<textarea name="invalidation_criteria" /></label>
          <label>Notes<textarea name="notes" /></label>
          <button>Add Forecast</button>
        </form>
      </section>

      <section className="panel">
        <h2>Open Position</h2>
        <form className="form" onSubmit={openPosition}>
          <div className="form-grid">
            <label>Linked Forecast<select name="linked_forecast_id" required>{forecasts.map((f) => <option value={f.id} key={f.id}>{new Date(f.timestamp).toLocaleString()} | edge {(f.edge_bps / 100).toFixed(2)}%</option>)}</select></label>
            <label>Side<select name="side"><option>YES</option><option>NO</option></select></label>
            <label>Entry Price %<input name="entry_price_pct" type="number" step="0.01" min="0" max="100" required /></label>
          </div>
          <div className="form-grid">
            <label>Quantity<input name="quantity" type="number" min="1" required /></label>
            <label>Fees $<input name="fees" type="number" step="0.01" min="0" defaultValue="0" /></label>
          </div>
          <label>Reason<textarea name="reason" /></label>
          <label>Notes<textarea name="notes" /></label>
          <button disabled={forecasts.length === 0}>Open Position</button>
          {forecasts.length === 0 && <div className="muted">Add a forecast before opening a position.</div>}
        </form>
      </section>

      <section className="panel">
        <h2>Resolve Market</h2>
        <form className="form" onSubmit={resolveMarket}>
          <div className="form-grid">
            <label>Final Outcome<select name="final_outcome"><option>YES</option><option>NO</option><option>VOID</option><option>AMBIGUOUS</option></select></label>
          </div>
          <label>Resolution Notes<textarea name="resolution_notes" /></label>
          <button className="secondary">Resolve</button>
        </form>
      </section>

      {positions.length > 0 && (
        <section className="panel">
          <h2>Position Actions</h2>
          <div className="muted">Use the position detail page to add buy/sell executions.</div>
        </section>
      )}
    </div>
  );
}
