import { apiGet, Market } from "@/lib/api";
import { KalshiImportForm } from "./KalshiImportForm";

export default async function MarketsPage() {
  const markets = await apiGet<Market[]>("/markets");

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Markets</h1>
          <div className="muted">Tracked Kalshi binary markets.</div>
        </div>
        <a className="button" href="/markets/new">New Market</a>
      </div>

      <KalshiImportForm />

      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>Market</th>
              <th>Category</th>
              <th>Status</th>
              <th>Expected Resolution</th>
            </tr>
          </thead>
          <tbody>
            {markets.map((market) => (
              <tr key={market.id}>
                <td><a href={`/markets/${market.id}`}>{market.title}</a></td>
                <td>{market.category}</td>
                <td><span className="pill">{market.status}</span></td>
                <td>{market.expected_resolution_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
