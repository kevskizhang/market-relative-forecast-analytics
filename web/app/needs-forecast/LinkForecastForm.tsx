"use client";

import { API_URL, Forecast, Position } from "@/lib/api";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

function forecastLabel(forecast: Forecast): string {
  const timestamp = new Date(forecast.timestamp).toLocaleString();
  const mine = (forecast.forecast_probability_yes_bps / 100).toFixed(2);
  const edge = (forecast.edge_bps / 100).toFixed(2);
  return `${timestamp} | mine ${mine}% | edge ${edge}%`;
}

export function LinkForecastForm({ position, forecasts }: { position: Position; forecasts: Forecast[] }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const forecastId = String(form.get("forecast_id") || "");
    if (!forecastId) {
      setError("Select a forecast to link.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/positions/${position.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ linked_forecast_id: forecastId }),
      });
      if (!response.ok) {
        setError(await response.text());
        return;
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not link forecast");
    } finally {
      setLoading(false);
    }
  }

  if (forecasts.length === 0) {
    return <a className="button secondary" href={`/markets/${position.market_id}`}>Add Forecast</a>;
  }

  return (
    <form className="inline-form" onSubmit={submit}>
      <select name="forecast_id" defaultValue={forecasts.length === 1 ? forecasts[0].id : ""} aria-label="Forecast to link">
        {forecasts.length > 1 && <option value="">Select forecast</option>}
        {forecasts.map((forecast) => (
          <option key={forecast.id} value={forecast.id}>{forecastLabel(forecast)}</option>
        ))}
      </select>
      <button disabled={loading}>{loading ? "Linking..." : forecasts.length === 1 ? "Use Only Forecast" : "Link Forecast"}</button>
      {error && <div className="error">{error}</div>}
    </form>
  );
}
