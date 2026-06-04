import { apiGet, Forecast } from "@/lib/api";
import { EditForecastForm } from "./EditForecastForm";

export default async function EditForecastPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const forecast = await apiGet<Forecast>(`/forecasts/${id}`);
  return (
    <div className="stack">
      <div>
        <h1>Edit Forecast</h1>
        <div className="muted">Correct a forecast entry mistake.</div>
      </div>
      <EditForecastForm forecast={forecast} />
    </div>
  );
}

