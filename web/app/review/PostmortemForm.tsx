"use client";

import { API_URL, Market, Position } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

const forecastErrorReasons = [
  "bad_base_rate",
  "bad_model",
  "missing_information",
  "overreacted_to_news",
  "underreacted_to_news",
  "resolution_misread",
  "variance",
  "other",
];

const tradeErrorReasons = [
  "none",
  "bad_entry",
  "bad_exit",
  "bad_sizing",
  "poor_liquidity",
  "ignored_spread",
  "premature_exit",
  "held_too_long",
  "other",
];

function optionalInt(value: FormDataEntryValue | null): number | null {
  if (!value) return null;
  return Number(value);
}

export function PostmortemForm({ market, position }: { market: Market; position?: Position }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const thesisValue = String(form.get("did_thesis_play_out") || "");
    const tags = String(form.get("mistake_tags") || "")
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    setError(null);
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/postmortems`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          market_id: market.id,
          position_id: position?.id ?? null,
          did_thesis_play_out: thesisValue === "" ? null : thesisValue === "true",
          forecast_error_reason: form.get("forecast_error_reason") || null,
          trade_error_reason: form.get("trade_error_reason") || null,
          execution_quality: optionalInt(form.get("execution_quality")),
          sizing_quality: optionalInt(form.get("sizing_quality")),
          exit_quality: optionalInt(form.get("exit_quality")),
          process_score: Number(form.get("process_score")),
          mistake_tags: tags.length > 0 ? tags : null,
          lesson: form.get("lesson"),
          notes: form.get("notes") || null,
        }),
      });
      if (!response.ok) {
        setError(await response.text());
        return;
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save postmortem");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="form review-form" onSubmit={submit}>
      <div className="callout">
        <strong>{market.title}</strong>
        {position && (
          <div className="muted">
            {position.side} position | P&amp;L {formatMoney(position.total_pnl_minor_units ?? position.realized_pnl_minor_units)}
          </div>
        )}
      </div>
      <div className="form-grid">
        <label>
          Thesis Played Out
          <select name="did_thesis_play_out" defaultValue="">
            <option value="">Not sure</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </label>
        <label>
          Process Score
          <select name="process_score" defaultValue="3" required>
            <option>1</option>
            <option>2</option>
            <option>3</option>
            <option>4</option>
            <option>5</option>
          </select>
        </label>
      </div>
      <div className="form-grid">
        <label>
          Forecast Error
          <select name="forecast_error_reason" defaultValue="">
            <option value="">None / unclear</option>
            {forecastErrorReasons.map((reason) => <option key={reason}>{reason}</option>)}
          </select>
        </label>
        <label>
          Trade Error
          <select name="trade_error_reason" defaultValue="none">
            {tradeErrorReasons.map((reason) => <option key={reason}>{reason}</option>)}
          </select>
        </label>
      </div>
      <div className="form-grid">
        <label>Execution Quality<select name="execution_quality" defaultValue=""><option value="">-</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
        <label>Sizing Quality<select name="sizing_quality" defaultValue=""><option value="">-</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
        <label>Exit Quality<select name="exit_quality" defaultValue=""><option value="">-</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
      </div>
      <label>Mistake Tags<input name="mistake_tags" placeholder="comma-separated, e.g. sizing, liquidity, weather-model" /></label>
      <label>Lesson<textarea name="lesson" required /></label>
      <label>Notes<textarea name="notes" /></label>
      {error && <div className="error">{error}</div>}
      <button disabled={loading}>{loading ? "Saving..." : "Save Postmortem"}</button>
    </form>
  );
}
