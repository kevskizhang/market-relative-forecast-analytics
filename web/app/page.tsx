import { apiGet } from "@/lib/api";
import { formatDate, formatMoney, pnlClass } from "@/lib/format";

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
    latest_kalshi_balance_minor_units: number | null;
    latest_kalshi_portfolio_value_minor_units: number | null;
  };
  data_health: {
    latest_raw_import_at: string | null;
    unconverted_fills: number;
    unconverted_settlements: number;
    positions_missing_forecast: number;
    resolved_markets_needing_review: number;
  };
};

function score(value: number | null) {
  return value === null ? "-" : value.toFixed(4);
}

export default async function DashboardPage() {
  const summary = await apiGet<Summary>("/dashboard/summary").catch(() => null);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <div className="eyebrow">Kalshi Forecast Journal</div>
          <h1>Dashboard</h1>
          <div className="muted">Sync trading activity from Kalshi, then add forecasts and reviews.</div>
        </div>
        <div className="page-actions">
          <a className="button secondary" href="/needs-forecast">Missing Forecasts</a>
          <a className="button" href="/settings/kalshi">Sync Kalshi</a>
        </div>
      </div>

      {!summary ? (
        <div className="panel">
          <h2>API unavailable</h2>
          <p className="muted">Start the Python API and refresh this page.</p>
        </div>
      ) : (
        <div className="dashboard-grid">
          <div className="stack">
            <section className="panel">
              <div className="section-head">
                <div>
                  <h2>Account State</h2>
                  <div className="muted">Latest account and open exposure snapshot.</div>
                </div>
                <span className="pill">Last sync {formatDate(summary.data_health.latest_raw_import_at)}</span>
              </div>
              <div className="metric-grid">
                <div className="metric-card">
                  <div className="muted">Kalshi Balance</div>
                  <div className="metric">{formatMoney(summary.exposure.latest_kalshi_balance_minor_units)}</div>
                </div>
                <div className="metric-card">
                  <div className="muted">Kalshi Portfolio Value</div>
                  <div className="metric">{formatMoney(summary.exposure.latest_kalshi_portfolio_value_minor_units)}</div>
                </div>
                <div className="metric-card">
                  <div className="muted">Open Cost Basis</div>
                  <div className="metric">{formatMoney(summary.exposure.open_exposure_minor_units)}</div>
                </div>
                <div className="metric-card">
                  <div className="muted">Manual Equity Snapshot</div>
                  <div className="metric">{formatMoney(summary.exposure.latest_total_equity_minor_units)}</div>
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="section-head">
                <div>
                  <h2>Trading</h2>
                  <div className="muted">{summary.trading.positions} total positions logged.</div>
                </div>
                <span className="pill status-open">{summary.trading.open_positions} open</span>
              </div>
              <div className="metric-grid">
                <div className="metric-card">
                  <div className="muted">Realized P&amp;L</div>
                  <div className={`metric ${pnlClass(summary.trading.realized_pnl_minor_units)}`}>
                    {formatMoney(summary.trading.realized_pnl_minor_units)}
                  </div>
                </div>
                <div className="metric-card">
                  <div className="muted">Total P&amp;L</div>
                  <div className={`metric ${pnlClass(summary.trading.total_pnl_minor_units)}`}>
                    {formatMoney(summary.trading.total_pnl_minor_units)}
                  </div>
                </div>
                <div className="metric-card">
                  <div className="muted">Open Positions</div>
                  <div className="metric">{summary.trading.open_positions}</div>
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="section-head">
                <div>
                  <h2>Forecasting</h2>
                  <div className="muted">{summary.forecasting.forecasts} forecasts logged.</div>
                </div>
                <span className="pill">{summary.forecasting.resolved_forecasts} scored</span>
              </div>
              <div className="metric-grid">
                <div className="metric-card">
                  <div className="muted">Avg Brier</div>
                  <div className="metric">{score(summary.forecasting.average_brier)}</div>
                </div>
                <div className="metric-card">
                  <div className="muted">Market Avg Brier</div>
                  <div className="metric">{score(summary.forecasting.average_market_brier)}</div>
                </div>
                <div className="metric-card">
                  <div className="muted">Brier Improvement</div>
                  <div className={`metric ${summary.forecasting.average_brier_improvement && summary.forecasting.average_brier_improvement > 0 ? "positive" : ""}`}>
                    {score(summary.forecasting.average_brier_improvement)}
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div className="stack">
            <section className="panel">
              <h2>Data Health</h2>
              <div className="stack">
                <div className="callout">
                  <div className="muted">Latest raw Kalshi import</div>
                  <strong>{formatDate(summary.data_health.latest_raw_import_at)}</strong>
                </div>
                <div className="metric-grid">
                  <div>
                    <div className="metric">{summary.data_health.unconverted_fills}</div>
                    <div className="muted">unconverted fills</div>
                  </div>
                  <div>
                    <div className="metric">{summary.data_health.unconverted_settlements}</div>
                    <div className="muted">unconverted settlements</div>
                  </div>
                  <div>
                    <div className="metric">{summary.data_health.positions_missing_forecast}</div>
                    <div className="muted">missing forecasts</div>
                  </div>
                  <div>
                    <div className="metric">{summary.data_health.resolved_markets_needing_review}</div>
                    <div className="muted">resolved markets</div>
                  </div>
                </div>
              </div>
            </section>

            <section className="panel">
              <h2>Next Actions</h2>
              <div className="stack">
                <a className="button secondary" href="/settings/kalshi">Sync Kalshi</a>
                <a className="button secondary" href="/needs-forecast">Add Missing Forecasts</a>
                <a className="button secondary" href="/markets">Review Markets</a>
                <a className="button secondary" href="/settings/export">Export Data</a>
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
