"use client";

import { API_URL, Forecast } from "@/lib/api";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

function bpsToPct(value: number): string {
  return (value / 100).toFixed(2);
}

function pctToBps(value: FormDataEntryValue | null): number {
  return Math.round(Number(value) * 100);
}

export function EditForecastForm({ forecast }: { forecast: Forecast }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError(null);
    const response = await fetch(`${API_URL}/forecasts/${forecast.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        market_probability_yes_bps: pctToBps(form.get("market_probability_yes_pct")),
        forecast_probability_yes_bps: pctToBps(form.get("forecast_probability_yes_pct")),
        confidence: Number(form.get("confidence")),
        thesis: form.get("thesis"),
        invalidation_criteria: form.get("invalidation_criteria"),
        research_quality: form.get("research_quality") || null,
        forecast_type: form.get("forecast_type"),
        notes: form.get("notes"),
      }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    router.push(`/markets/${forecast.market_id}`);
    router.refresh();
  }

  async function deleteForecast() {
    if (!confirm("Delete this forecast? Linked positions will be unlinked.")) return;
    const response = await fetch(`${API_URL}/forecasts/${forecast.id}`, { method: "DELETE" });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    router.push(`/markets/${forecast.market_id}`);
    router.refresh();
  }

  return (
    <form className="form panel" onSubmit={submit}>
      <div className="form-grid">
        <label>Market YES %<input name="market_probability_yes_pct" type="number" step="0.01" min="0" max="100" required defaultValue={bpsToPct(forecast.market_probability_yes_bps)} /></label>
        <label>Your YES %<input name="forecast_probability_yes_pct" type="number" step="0.01" min="0" max="100" required defaultValue={bpsToPct(forecast.forecast_probability_yes_bps)} /></label>
        <label>Confidence<select name="confidence" defaultValue={forecast.confidence}><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
      </div>
      <div className="form-grid">
        <label>Research Quality<select name="research_quality" defaultValue={forecast.research_quality ?? ""}><option value="">-</option><option>low</option><option>medium</option><option>high</option></select></label>
        <label>Forecast Type<select name="forecast_type" defaultValue={forecast.forecast_type}><option>initial</option><option>update</option><option>pre_trade</option><option>post_news</option><option>pre_resolution</option></select></label>
      </div>
      <label>Thesis<textarea name="thesis" required defaultValue={forecast.thesis} /></label>
      <label>Invalidation Criteria<textarea name="invalidation_criteria" defaultValue={forecast.invalidation_criteria ?? ""} /></label>
      <label>Notes<textarea name="notes" defaultValue={forecast.notes ?? ""} /></label>
      {error && <div className="error">{error}</div>}
      <div style={{ display: "flex", gap: 10 }}>
        <button>Save Forecast</button>
        <button type="button" className="secondary" onClick={deleteForecast}>Delete</button>
        <a className="button secondary" href={`/markets/${forecast.market_id}`}>Cancel</a>
      </div>
    </form>
  );
}

