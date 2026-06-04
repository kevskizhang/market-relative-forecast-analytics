"use client";

import { API_URL } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useState } from "react";

type RebuildResult = {
  deleted_positions: number;
  deleted_executions: number;
  converted_fills: number;
  converted_settlements: number;
};

export function RebuildKalshiButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RebuildResult | null>(null);

  async function rebuild() {
    if (!confirm("Rebuild imported Kalshi positions/executions from raw Kalshi records? Manual forecasts are preserved, but imported position links may need review.")) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(`${API_URL}/kalshi/rebuild-derived`, { method: "POST" });
      if (!response.ok) {
        setError(await response.text());
        return;
      }
      setResult(await response.json());
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? `${err.message}. Confirm the API is running at ${API_URL}.` : "Rebuild failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="stack">
      <button type="button" className="secondary" onClick={rebuild} disabled={loading}>
        {loading ? "Rebuilding..." : "Rebuild Imported Positions"}
      </button>
      {error && <div className="error">{error}</div>}
      {result && (
        <div className="muted">
          Deleted {result.deleted_positions} positions and {result.deleted_executions} executions. Converted {result.converted_fills} fills and {result.converted_settlements} settlements.
        </div>
      )}
    </div>
  );
}
