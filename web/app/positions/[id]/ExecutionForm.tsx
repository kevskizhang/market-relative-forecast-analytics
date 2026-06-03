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

export function ExecutionForm({ position, forecasts }: { position: Position; forecasts: Forecast[] }) {
  const router = useRouter();
  const [action, setAction] = useState("sell");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setError(null);
    const form = new FormData(formElement);
    const response = await fetch(`${API_URL}/positions/${position.id}/executions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: form.get("action"),
        side: position.side,
        price_bps: pctToBps(form.get("price_pct")),
        quantity: Number(form.get("quantity")),
        fees_minor_units: dollarsToCents(form.get("fees")),
        order_type: "manual",
        reason: form.get("reason"),
        notes: form.get("notes"),
        linked_forecast_id: form.get("linked_forecast_id") || null,
      }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    formElement.reset();
    router.refresh();
  }

  return (
    <section className="panel">
      <h2>Add Execution</h2>
      <form className="form" onSubmit={submit}>
        <div className="form-grid">
          <label>Action<select name="action" value={action} onChange={(e) => setAction(e.target.value)}><option value="sell">sell</option><option value="buy">buy</option></select></label>
          <label>Price %<input name="price_pct" type="number" step="0.01" min="0" max="100" required /></label>
          <label>Quantity<input name="quantity" type="number" min="1" max={action === "sell" ? position.quantity : undefined} required /></label>
          <label>Fees $<input name="fees" type="number" min="0" step="0.01" defaultValue="0" /></label>
        </div>
        {action === "buy" && (
          <label>Fresh Forecast<select name="linked_forecast_id" required><option value="">Select forecast</option>{forecasts.map((forecast) => <option key={forecast.id} value={forecast.id}>{new Date(forecast.timestamp).toLocaleString()} | edge {(forecast.edge_bps / 100).toFixed(2)}%</option>)}</select></label>
        )}
        <label>Reason<textarea name="reason" /></label>
        <label>Notes<textarea name="notes" /></label>
        {error && <div className="error">{error}</div>}
        <button>Add Execution</button>
      </form>
    </section>
  );
}
