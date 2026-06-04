"use client";

import { API_URL, Forecast, KalshiMarket, Position } from "@/lib/api";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

function pctToBps(value: FormDataEntryValue | null): number {
  return Math.round(Number(value) * 100);
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

async function patch(path: string, payload: unknown) {
  const response = await fetch(`${API_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export function MarketActions({
  marketId,
  kalshiTicker,
  forecasts,
  positions,
}: {
  marketId: string;
  kalshiTicker?: string | null;
  forecasts: Forecast[];
  positions: Position[];
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [marketPct, setMarketPct] = useState("");
  const [yesBidPct, setYesBidPct] = useState("");
  const [yesAskPct, setYesAskPct] = useState("");
  const [lastTradePct, setLastTradePct] = useState("");
  const positionsMissingForecast = positions.filter((position) => !position.linked_forecast_id);

  function bpsToPctInput(value?: number | null): string {
    if (value === null || value === undefined) return "";
    return (value / 100).toFixed(2);
  }

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
      const forecast = await post(`/markets/${marketId}/forecasts`, {
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
      const linkedPositionId = String(form.get("linked_position_id") || "");
      if (linkedPositionId) {
        await patch(`/positions/${linkedPositionId}`, {
          linked_forecast_id: forecast.id,
        });
      }
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

  async function fetchKalshiPrice() {
    if (!kalshiTicker) {
      setError("Add a Kalshi ticker to this market before fetching live pricing.");
      return;
    }
    setError(null);
    const response = await fetch(`${API_URL}/kalshi/markets/${encodeURIComponent(kalshiTicker)}`);
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    const market = (await response.json()) as KalshiMarket;
    setMarketPct(bpsToPctInput(market.market_probability_yes_bps));
    setYesBidPct(bpsToPctInput(market.yes_bid_bps));
    setYesAskPct(bpsToPctInput(market.yes_ask_bps));
    setLastTradePct(bpsToPctInput(market.last_trade_price_bps));
  }

  async function syncKalshiSnapshot() {
    setError(null);
    const response = await fetch(`${API_URL}/markets/${marketId}/snapshots/kalshi`, { method: "POST" });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    router.refresh();
  }

  async function syncKalshiMetadata() {
    setError(null);
    const response = await fetch(`${API_URL}/markets/${marketId}/sync-kalshi`, { method: "POST" });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    router.refresh();
  }

  return (
    <div className="stack">
      {error && <div className="panel error">{error}</div>}

      <section className="panel">
        <h2>Add Snapshot and Forecast</h2>
        <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <button type="button" className="secondary" onClick={syncKalshiMetadata}>Sync Kalshi Metadata</button>
          <button type="button" className="secondary" onClick={fetchKalshiPrice}>Prefill Live Kalshi Price</button>
          <button type="button" className="secondary" onClick={syncKalshiSnapshot}>Save Kalshi Snapshot Only</button>
        </div>
        <form className="form" onSubmit={addSnapshotForecast}>
          <div className="form-grid">
            <label>Market YES %<input name="market_probability_yes_pct" type="number" step="0.01" min="0" max="100" required value={marketPct} onChange={(event) => setMarketPct(event.target.value)} /></label>
            <label>Your YES %<input name="forecast_probability_yes_pct" type="number" step="0.01" min="0" max="100" required /></label>
            <label>Confidence<select name="confidence" defaultValue="3"><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
          </div>
          <div className="form-grid">
            <label>YES Bid %<input name="yes_bid_pct" type="number" step="0.01" min="0" max="100" value={yesBidPct} onChange={(event) => setYesBidPct(event.target.value)} /></label>
            <label>YES Ask %<input name="yes_ask_pct" type="number" step="0.01" min="0" max="100" value={yesAskPct} onChange={(event) => setYesAskPct(event.target.value)} /></label>
            <label>Last Trade %<input name="last_trade_price_pct" type="number" step="0.01" min="0" max="100" value={lastTradePct} onChange={(event) => setLastTradePct(event.target.value)} /></label>
          </div>
          <div className="form-grid">
            <label>Research Quality<select name="research_quality" defaultValue="medium"><option value="">-</option><option>low</option><option>medium</option><option>high</option></select></label>
            <label>Forecast Type<select name="forecast_type" defaultValue="initial"><option>initial</option><option>update</option><option>pre_trade</option><option>post_news</option><option>pre_resolution</option></select></label>
          </div>
          {positionsMissingForecast.length > 0 && (
            <label>
              Attach to Position
              <select name="linked_position_id" defaultValue={positionsMissingForecast[0]?.id ?? ""}>
                <option value="">Do not attach</option>
                {positionsMissingForecast.map((position) => (
                  <option key={position.id} value={position.id}>
                    {position.side} | {Number(position.quantity).toLocaleString(undefined, { maximumFractionDigits: 6 })} contracts | opened {new Date(position.opened_at).toLocaleString()}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>Thesis<textarea name="thesis" required /></label>
          <label>Invalidation Criteria<textarea name="invalidation_criteria" /></label>
          <label>Notes<textarea name="notes" /></label>
          <button>Add Forecast</button>
        </form>
      </section>

      <section className="panel">
        <h2>Trade Data</h2>
        <p className="muted">Buys, sells, fees, positions, and settlements should come from Kalshi sync. Use manual trade entry only as a fallback outside the main workflow.</p>
        <a className="button secondary" href="/settings/kalshi">Sync Kalshi</a>
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
    </div>
  );
}
