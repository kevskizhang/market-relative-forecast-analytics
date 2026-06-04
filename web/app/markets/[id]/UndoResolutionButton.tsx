"use client";

import { API_URL } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function UndoResolutionButton({ marketId }: { marketId: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function undo() {
    if (!confirm("Undo this market resolution? Forecast scores will be removed and the market can be resolved again.")) return;
    setLoading(true);
    setError(null);
    const response = await fetch(`${API_URL}/markets/${marketId}/resolution`, { method: "DELETE" });
    setLoading(false);
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    router.refresh();
  }

  return (
    <div>
      <button type="button" className="secondary" onClick={undo} disabled={loading}>
        {loading ? "Undoing..." : "Undo Resolution"}
      </button>
      {error && <div className="error">{error}</div>}
    </div>
  );
}

