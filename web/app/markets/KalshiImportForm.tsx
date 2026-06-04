"use client";

import { API_URL } from "@/lib/api";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export function KalshiImportForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setError(null);
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/kalshi/import-market`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: form.get("ticker") }),
      });
      if (!response.ok) {
        setError(await response.text());
        return;
      }
      const market = await response.json();
      formElement.reset();
      router.push(`/markets/${market.id}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? `${err.message}. Confirm the API is running at ${API_URL} and that you opened the web app at http://localhost:3000.`
          : "Import failed. Confirm the API is running."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <h2>Import Kalshi Market</h2>
      <form className="form" onSubmit={submit}>
        <div className="form-grid">
          <label>Kalshi Ticker or URL<input name="ticker" required placeholder="KX..." /></label>
        </div>
        {error && <div className="error">{error}</div>}
        <button disabled={saving}>{saving ? "Importing..." : "Import Market"}</button>
      </form>
    </section>
  );
}
