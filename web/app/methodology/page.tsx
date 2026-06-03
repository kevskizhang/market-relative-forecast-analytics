export default function MethodologyPage() {
  return (
    <div className="stack">
      <div>
        <h1>Methodology</h1>
        <div className="muted">How the app scores forecasts and trades.</div>
      </div>
      <section className="panel">
        <h2>Forecasts</h2>
        <p>Forecasts are immutable snapshots. Updating a probability creates a new record.</p>
        <p>Edge is your YES probability minus the market-implied YES probability.</p>
        <pre>{`edge_bps = forecast_probability_yes_bps - market_probability_yes_bps`}</pre>
      </section>
      <section className="panel">
        <h2>Brier Score</h2>
        <p>YES outcomes score against 10000 basis points. NO outcomes score against 0.</p>
        <pre>{`brier_user = (forecast_probability_yes_bps - outcome_value_bps)^2
brier_market = (market_probability_yes_bps - outcome_value_bps)^2
brier_improvement = brier_market - brier_user`}</pre>
      </section>
      <section className="panel">
        <h2>Positions</h2>
        <p>Executions are the accounting source of truth. Partial exits use average-cost accounting for MVP.</p>
        <pre>{`realized_pnl = sell_net_proceeds - cost_basis_of_sold_shares`}</pre>
      </section>
    </div>
  );
}

