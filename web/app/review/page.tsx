import { apiGet, Market, Position, Postmortem } from "@/lib/api";
import { formatDate, formatMoney, formatQuantity, pnlClass, statusClass } from "@/lib/format";
import { PostmortemForm } from "./PostmortemForm";

const reviewablePositionStatuses = new Set(["closed_before_resolution", "resolved", "voided"]);

export default async function ReviewPage() {
  const [markets, positions, postmortems] = await Promise.all([
    apiGet<Market[]>("/markets"),
    apiGet<Position[]>("/positions"),
    apiGet<Postmortem[]>("/postmortems"),
  ]);
  const marketById = new Map(markets.map((market) => [market.id, market]));
  const reviewedPositionIds = new Set(postmortems.map((postmortem) => postmortem.position_id).filter(Boolean));
  const reviewedMarketIds = new Set(postmortems.filter((postmortem) => !postmortem.position_id).map((postmortem) => postmortem.market_id));
  const reviewQueue = positions.filter(
    (position) => reviewablePositionStatuses.has(position.status) && !reviewedPositionIds.has(position.id)
  );
  const marketOnlyQueue = markets.filter(
    (market) =>
      ["resolved", "voided", "ambiguous"].includes(market.status) &&
      !reviewedMarketIds.has(market.id) &&
      !positions.some((position) => position.market_id === market.id)
  );

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <div className="eyebrow">Process Review</div>
          <h1>Postmortems</h1>
          <div className="muted">Review closed positions and resolved markets while the decision is still fresh.</div>
        </div>
        <span className={reviewQueue.length + marketOnlyQueue.length > 0 ? "pill status-missing" : "pill status-resolved"}>
          {reviewQueue.length + marketOnlyQueue.length} pending
        </span>
      </div>

      <section className="panel">
        <div className="section-head">
          <div>
            <h2>Review Queue</h2>
            <div className="muted">Closed or resolved positions without a postmortem.</div>
          </div>
        </div>
        {reviewQueue.length === 0 && marketOnlyQueue.length === 0 ? (
          <div className="empty">No postmortems are pending.</div>
        ) : (
          <div className="stack">
            {reviewQueue.map((position) => {
              const market = marketById.get(position.market_id);
              const pnl = position.total_pnl_minor_units ?? position.realized_pnl_minor_units;
              if (!market) return null;
              return (
                <details className="panel nested-panel" key={position.id}>
                  <summary>
                    <span>{market.title}</span>
                    <span className={statusClass(position.status)}>{position.status}</span>
                    <span>{position.side}</span>
                    <span>{formatQuantity(position.quantity)} open</span>
                    <span className={pnlClass(pnl)}>{formatMoney(pnl)}</span>
                  </summary>
                  <PostmortemForm market={market} position={position} />
                </details>
              );
            })}
            {marketOnlyQueue.map((market) => (
              <details className="panel nested-panel" key={market.id}>
                <summary>
                  <span>{market.title}</span>
                  <span className={statusClass(market.status)}>{market.status}</span>
                  <span>Outcome {market.final_outcome ?? "-"}</span>
                </summary>
                <PostmortemForm market={market} />
              </details>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Recent Reviews</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Reviewed</th><th>Market</th><th>Process</th><th>Thesis</th><th>Lesson</th></tr></thead>
            <tbody>
              {postmortems.slice(0, 20).map((postmortem) => {
                const market = marketById.get(postmortem.market_id);
                return (
                  <tr key={postmortem.id}>
                    <td>{formatDate(postmortem.reviewed_at)}</td>
                    <td>{market ? <a href={`/markets/${market.id}`}>{market.title}</a> : postmortem.market_id}</td>
                    <td>{postmortem.process_score}/5</td>
                    <td>{postmortem.did_thesis_play_out === null || postmortem.did_thesis_play_out === undefined ? "-" : postmortem.did_thesis_play_out ? "yes" : "no"}</td>
                    <td>{postmortem.lesson}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {postmortems.length === 0 && <div className="empty">No postmortems logged yet.</div>}
      </section>
    </div>
  );
}
