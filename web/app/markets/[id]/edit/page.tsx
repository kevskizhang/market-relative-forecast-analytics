import { apiGet, Market } from "@/lib/api";
import { EditMarketForm } from "./EditMarketForm";

export default async function EditMarketPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const market = await apiGet<Market>(`/markets/${id}`);

  return (
    <div className="stack">
      <div>
        <h1>Edit Market</h1>
        <div className="muted">{market.title}</div>
      </div>
      <EditMarketForm market={market} />
    </div>
  );
}

