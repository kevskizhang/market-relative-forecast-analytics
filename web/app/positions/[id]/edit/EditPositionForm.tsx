"use client";

import { API_URL, Forecast, Position } from "@/lib/api";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

function datetimeLocal(value: string): string {
  const date = new Date(value);
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

export function EditPositionForm({ position, forecasts }: { position: Position; forecasts: Forecast[] }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError(null);
    const openedAt = form.get("opened_at");
    const response = await fetch(`${API_URL}/positions/${position.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        linked_forecast_id: form.get("linked_forecast_id") || null,
        opened_at: openedAt ? new Date(String(openedAt)).toISOString() : null,
        position_notes: form.get("position_notes"),
      }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    router.push(`/positions/${position.id}`);
    router.refresh();
  }

  async function deletePosition() {
    if (!confirm("Delete this position and its executions? This cannot be undone.")) return;
    const response = await fetch(`${API_URL}/positions/${position.id}`, { method: "DELETE" });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    router.push(`/markets/${position.market_id}`);
    router.refresh();
  }

  return (
    <form className="form panel" onSubmit={submit}>
      <div className="form-grid">
        <label>
          Linked Forecast
          <select name="linked_forecast_id" defaultValue={position.linked_forecast_id ?? ""}>
            <option value="">None</option>
            {forecasts.map((forecast) => (
              <option key={forecast.id} value={forecast.id}>
                {new Date(forecast.timestamp).toLocaleString()} | edge {(forecast.edge_bps / 100).toFixed(2)}%
              </option>
            ))}
          </select>
        </label>
        <label>Opened At<input name="opened_at" type="datetime-local" defaultValue={datetimeLocal(position.opened_at)} /></label>
      </div>
      <label>Notes<textarea name="position_notes" defaultValue={position.position_notes ?? ""} /></label>
      <div className="muted">To correct quantity, price, side, or fees, delete this position and re-enter it so execution accounting stays consistent.</div>
      {error && <div className="error">{error}</div>}
      <div style={{ display: "flex", gap: 10 }}>
        <button>Save Position</button>
        <button type="button" className="secondary" onClick={deletePosition}>Delete</button>
        <a className="button secondary" href={`/positions/${position.id}`}>Cancel</a>
      </div>
    </form>
  );
}

