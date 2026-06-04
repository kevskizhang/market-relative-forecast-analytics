import { apiGet, Execution, Forecast, ForecastScore, Market, Position, Postmortem, Snapshot } from "@/lib/api";
import { forecastEdgeStats } from "@/lib/forecastEdges";
import { formatBps, formatDate, formatMoney, formatQuantity, pnlClass, signedBpsClass, statusClass } from "@/lib/format";

function scoreDisplay(value?: number | null): string {
  if (value === null || value === undefined) return "-";
  return (value / 100000000).toFixed(4);
}

export default async function ForecastDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const forecast = await apiGet<Forecast>(`/forecasts/${id}`);
  const [market, snapshots, positions, scores, postmortems] = await Promise.all([
    apiGet<Market>(`/markets/${forecast.market_id}`),
    apiGet<Snapshot[]>(`/markets/${forecast.market_id}/snapshots`),
    apiGet<Position[]>(`/markets/${forecast.market_id}/positions`),
    apiGet<ForecastScore[]>(`/markets/${forecast.market_id}/scores`),
    apiGet<Postmortem[]>("/postmortems"),
  ]);
  const snapshot = forecast.market_snapshot_id ? snapshots.find((item) => item.id === forecast.market_snapshot_id) : undefined;
  const stats = forecastEdgeStats(forecast, snapshot);
  const linkedPositions = positions.filter((position) => position.linked_forecast_id === forecast.id);
  const score = scores.find((item) => item.forecast_id === forecast.id);
  const linkedPositionIds = new Set(linkedPositions.map((position) => position.id));
  const relatedPostmortems = postmortems.filter(
    (postmortem) => postmortem.market_id === market.id && (!postmortem.position_id || linkedPositionIds.has(postmortem.position_id))
  );
  const executionsByPosition = new Map<string, Execution[]>(
    await Promise.all(
      linkedPositions.map(async (position) => [
        position.id,
        await apiGet<Execution[]>(`/positions/${position.id}/executions`),
      ] as const)
    )
  );

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <div className="eyebrow">Forecast</div>
          <h1>{market.title}</h1>
          <div className="muted">Logged {formatDate(forecast.timestamp)} | {forecast.forecast_type}</div>
        </div>
        <div className="page-actions">
          <a className="button secondary" href={`/markets/${market.id}`}>Market</a>
          <a className="button secondary" href={`/forecasts/${forecast.id}/edit`}>Edit</a>
          <span className={statusClass(forecast.status)}>{forecast.status}</span>
        </div>
      </div>

      <section className="panel">
        <div className="metric-grid">
          <div className="metric-card"><div className="muted">Your YES</div><div className="metric">{formatBps(forecast.forecast_probability_yes_bps)}</div></div>
          <div className="metric-card"><div className="muted">Market Mid</div><div className="metric">{formatBps(stats.yesMid)}</div></div>
          <div className="metric-card"><div className="muted">Edge vs Mid</div><div className={`metric ${signedBpsClass(stats.edgeVsMid).replace("numeric", "")}`}>{formatBps(stats.edgeVsMid)}</div></div>
          <div className="metric-card"><div className="muted">Best Executable Edge</div><div className={`metric ${signedBpsClass(stats.bestExecutableEdge).replace("numeric", "")}`}>{formatBps(stats.bestExecutableEdge)}</div></div>
        </div>
      </section>

      <section className="panel">
        <h2>Execution Context</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th className="numeric">YES Bid</th><th className="numeric">YES Ask</th><th className="numeric">Mid</th><th className="numeric">Spread</th><th className="numeric">Buy YES</th><th className="numeric">Buy NO</th><th className="numeric">Sell YES</th><th className="numeric">Sell NO</th><th className="numeric">Spread Penalty</th></tr></thead>
            <tbody>
              <tr>
                <td className="numeric">{formatBps(stats.yesBid)}</td>
                <td className="numeric">{formatBps(stats.yesAsk)}</td>
                <td className="numeric">{formatBps(stats.yesMid)}</td>
                <td className="numeric">{formatBps(stats.spread)}</td>
                <td className={signedBpsClass(stats.edgeBuyYes)}>{formatBps(stats.edgeBuyYes)}</td>
                <td className={signedBpsClass(stats.edgeBuyNo)}>{formatBps(stats.edgeBuyNo)}</td>
                <td className={signedBpsClass(stats.edgeSellYes)}>{formatBps(stats.edgeSellYes)}</td>
                <td className={signedBpsClass(stats.edgeSellNo)}>{formatBps(stats.edgeSellNo)}</td>
                <td className={signedBpsClass(stats.spreadPenalty !== null ? -stats.spreadPenalty : null)}>{formatBps(stats.spreadPenalty)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2>Reasoning</h2>
        <div className="stack">
          <div><h3>Thesis</h3><p>{forecast.thesis}</p></div>
          {forecast.invalidation_criteria && <div><h3>Invalidation Criteria</h3><p>{forecast.invalidation_criteria}</p></div>}
          {forecast.notes && <div><h3>Notes</h3><p>{forecast.notes}</p></div>}
          <div className="grid">
            <div className="callout"><div className="muted">Confidence</div><strong>{forecast.confidence}/5</strong></div>
            <div className="callout"><div className="muted">Research Quality</div><strong>{forecast.research_quality ?? "-"}</strong></div>
          </div>
        </div>
      </section>

      {linkedPositions.length > 0 && (
        <section className="panel">
          <h2>Linked Positions</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Opened</th><th>Side</th><th>Status</th><th className="numeric">Qty</th><th className="numeric">Avg Entry</th><th className="numeric">P&amp;L</th></tr></thead>
              <tbody>
                {linkedPositions.map((position) => {
                  const pnl = position.total_pnl_minor_units ?? position.realized_pnl_minor_units;
                  return (
                    <tr key={position.id}>
                      <td><a href={`/positions/${position.id}`}>{formatDate(position.opened_at)}</a></td>
                      <td>{position.side}</td>
                      <td><span className={statusClass(position.status)}>{position.status}</span></td>
                      <td className="numeric">{formatQuantity(position.quantity)}</td>
                      <td className="numeric">{formatBps(position.average_entry_price_bps)}</td>
                      <td className={`numeric ${pnlClass(pnl)}`}>{formatMoney(pnl)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="timeline">
            {linkedPositions.flatMap((position) =>
              (executionsByPosition.get(position.id) ?? []).map((execution) => (
                <div className="timeline-item" key={execution.id}>
                  <strong>{execution.action} {execution.side} {formatQuantity(execution.quantity)} @ {formatBps(execution.price_bps)}</strong>
                  <div className="muted">{formatDate(execution.timestamp)} | fees {formatMoney(execution.fees_minor_units)}</div>
                </div>
              ))
            )}
          </div>
        </section>
      )}

      {(score || relatedPostmortems.length > 0) && (
        <section className="panel">
          <h2>Outcome Review</h2>
          {score && (
            <div className="metric-grid">
              <div className="metric-card"><div className="muted">Brier</div><div className="metric">{scoreDisplay(score.brier_user_bps_squared)}</div></div>
              <div className="metric-card"><div className="muted">Market Brier</div><div className="metric">{scoreDisplay(score.brier_market_bps_squared)}</div></div>
              <div className="metric-card"><div className="muted">Improvement</div><div className={`metric ${score.brier_improvement_bps_squared >= 0 ? "positive" : "negative"}`}>{scoreDisplay(score.brier_improvement_bps_squared)}</div></div>
            </div>
          )}
          {relatedPostmortems.map((postmortem) => (
            <div className="callout" key={postmortem.id}>
              <div className="muted">{formatDate(postmortem.reviewed_at)} | process {postmortem.process_score}/5</div>
              <strong>{postmortem.lesson}</strong>
              {postmortem.notes && <p>{postmortem.notes}</p>}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
