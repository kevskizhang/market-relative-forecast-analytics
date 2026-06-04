"use client";

import { API_URL, Market } from "@/lib/api";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export function EditMarketForm({ market }: { market: Market }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setSaving(true);
    setError(null);
    const form = new FormData(formElement);
    const payload = Object.fromEntries(form.entries());
    const response = await fetch(`${API_URL}/markets/${market.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSaving(false);
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    router.push(`/markets/${market.id}`);
    router.refresh();
  }

  return (
    <form className="form panel" onSubmit={submit}>
      <div className="form-grid">
        <label>Title<input name="title" required defaultValue={market.title} /></label>
        <label>Kalshi Ticker<input name="platform_market_id" defaultValue={market.platform_market_id ?? ""} /></label>
      </div>
      <div className="form-grid">
        <label>Category<input name="category" required defaultValue={market.category} /></label>
        <label>Expected Resolution<input name="expected_resolution_date" type="date" required defaultValue={market.expected_resolution_date} /></label>
      </div>
      <label>Market URL<input name="market_url" type="url" defaultValue={market.market_url ?? ""} /></label>
      <label>Resolution Criteria<textarea name="resolution_criteria" required defaultValue={market.resolution_criteria} /></label>
      <label>Description<textarea name="description" defaultValue={market.description ?? ""} /></label>
      <label>Notes<textarea name="notes" defaultValue={market.notes ?? ""} /></label>
      {error && <div className="error">{error}</div>}
      <div style={{ display: "flex", gap: 10 }}>
        <button disabled={saving}>{saving ? "Saving..." : "Save Changes"}</button>
        <a className="button secondary" href={`/markets/${market.id}`}>Cancel</a>
      </div>
    </form>
  );
}

