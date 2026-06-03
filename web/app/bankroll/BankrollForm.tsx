"use client";

import { API_URL } from "@/lib/api";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

function dollarsToCents(value: FormDataEntryValue | null): number {
  return Math.round(Number(value || 0) * 100);
}

export function BankrollForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setError(null);
    const form = new FormData(formElement);
    const response = await fetch(`${API_URL}/bankroll-snapshots`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cash_balance_minor_units: dollarsToCents(form.get("cash")),
        open_position_value_minor_units: dollarsToCents(form.get("open_value")),
        notes: form.get("notes"),
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
    <form className="form panel" onSubmit={submit}>
      <h2>Add Bankroll Snapshot</h2>
      <div className="form-grid">
        <label>Cash $<input name="cash" type="number" min="0" step="0.01" required /></label>
        <label>Open Position Value $<input name="open_value" type="number" min="0" step="0.01" required /></label>
      </div>
      <label>Notes<textarea name="notes" /></label>
      {error && <div className="error">{error}</div>}
      <button>Add Snapshot</button>
    </form>
  );
}
