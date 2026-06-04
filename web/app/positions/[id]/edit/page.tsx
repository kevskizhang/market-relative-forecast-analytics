import { apiGet, Forecast, Position } from "@/lib/api";
import { EditPositionForm } from "./EditPositionForm";

export default async function EditPositionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const position = await apiGet<Position>(`/positions/${id}`);
  const forecasts = await apiGet<Forecast[]>(`/markets/${position.market_id}/forecasts`);
  return (
    <div className="stack">
      <div>
        <h1>Edit Position</h1>
        <div className="muted">Correct position metadata or delete a bad entry.</div>
      </div>
      <EditPositionForm position={position} forecasts={forecasts} />
    </div>
  );
}

