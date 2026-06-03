import { NewMarketForm } from "./NewMarketForm";

export default function NewMarketPage() {
  return (
    <div className="stack">
      <div>
        <h1>New Market</h1>
        <div className="muted">Create the event before logging forecasts or trades.</div>
      </div>
      <NewMarketForm />
    </div>
  );
}

