import { apiGet } from "@/lib/api";
import { formatMoney } from "@/lib/format";

type Summary = {
  forecasting: {
    forecasts: number;
    resolved_forecasts: number;
    average_brier: number | null;
    average_market_brier: number | null;
    average_brier_improvement: number | null;
  };
  trading: {
    positions: number;
    open_positions: number;
    realized_pnl_minor_units: number;
    total_pnl_minor_units: number;
  };
  exposure: {
    open_exposure_minor_units: number;
    latest_total_equity_minor_units: number | null;
  };
};

export default async function DashboardPage() {
  const summary = await apiGet<Summary>("/dashboard/summary").catch(() => null);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <div className="muted">Manual Kalshi forecast and trade logging.</div>
        </div>
        <a className="button" href="/markets/new">New Market</a>
      </div>

      {!summary ? (
        <div className="panel">
          <h2>API unavailable</h2>
          <p className="muted">Start the Python API and refresh this page.</p>
        </div>
      ) : (
        <div className="grid">
          <section className="panel">
            <h2>Forecasting</h2>
            <div className="metric">{summary.forecasting.forecasts}</div>
            <div className="muted">forecasts logged</div>
            <p>Resolved: {summary.forecasting.resolved_forecasts}</p>
            <p>Avg Brier: {summary.forecasting.average_brier ?? "-"}</p>
            <p>Market-relative: {summary.forecasting.average_brier_improvement ?? "-"}</p>
          </section>

          <section className="panel">
            <h2>Trading</h2>
            <div className="metric">{summary.trading.open_positions}</div>
            <div className="muted">open positions</div>
            <p>Realized P&amp;L: {formatMoney(summary.trading.realized_pnl_minor_units)}</p>
            <p>Total P&amp;L: {formatMoney(summary.trading.total_pnl_minor_units)}</p>
          </section>

          <section className="panel">
            <h2>Exposure</h2>
            <div className="metric">{formatMoney(summary.exposure.open_exposure_minor_units)}</div>
            <div className="muted">open cost basis</div>
            <p>Latest equity: {formatMoney(summary.exposure.latest_total_equity_minor_units)}</p>
          </section>
        </div>
      )}
    </div>
  );
}

