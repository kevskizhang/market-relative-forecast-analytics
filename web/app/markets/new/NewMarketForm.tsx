"use client";

import { API_URL } from "@/lib/api";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export function NewMarketForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    const response = await fetch(`${API_URL}/markets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSaving(false);
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    const market = await response.json();
    router.push(`/markets/${market.id}`);
  }

  return (
    <form className="form panel" onSubmit={submit}>
      <div className="form-grid">
        <label>Title<input name="title" required /></label>
        <label>Kalshi Ticker<input name="platform_market_id" /></label>
      </div>
      <div className="form-grid">
        <label>Category<input name="category" required /></label>
        <label>Expected Resolution<input name="expected_resolution_date" type="date" required /></label>
      </div>
      <label>Market URL<input name="market_url" type="url" /></label>
      <label>Resolution Criteria<textarea name="resolution_criteria" required /></label>
      <label>Description<textarea name="description" /></label>
      <label>Notes<textarea name="notes" /></label>
      {error && <div className="error">{error}</div>}
      <button disabled={saving}>{saving ? "Saving..." : "Create Market"}</button>
    </form>
  );
}

