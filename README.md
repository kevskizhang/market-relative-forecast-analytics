# Market-Relative Forecast Analytics

Personal Kalshi forecast journal for syncing prediction-market activity from Kalshi, then adding subjective probabilities, thesis notes, reviews, and market-relative scoring.

## Development

The default development setup uses:

- Supabase Postgres for the database.
- A repo-local Python virtual environment for the FastAPI backend.
- Local Next.js for the frontend.

## Supabase Setup

Copy the API environment template:

```powershell
Copy-Item api\.env.example api\.env
```

Then edit `api\.env` and fill in `DATABASE_URL` from Supabase.

Supabase usually gives you a standard PostgreSQL URL:

```text
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

The app automatically converts `postgresql://` to SQLAlchemy's installed `psycopg` driver internally, so you do not need to add `+psycopg` yourself.

The exact host and username may differ by Supabase region and connection mode. If your password contains special characters, URL-encode it.

Kalshi public market data does not require credentials for the current MVP integration. Optional overrides:

```text
KALSHI_API_BASE_URL=https://external-api.kalshi.com/trade-api/v2
KALSHI_WEB_BASE_URL=https://kalshi.com
```

Authenticated fill import requires a Kalshi API key:

1. Open Kalshi account settings.
2. Go to the API Keys section.
3. Create a read-only key if Kalshi offers scopes.
4. Save the private key file somewhere outside the repo.
5. Add these to `api\.env`:

```text
KALSHI_ACCESS_KEY=<key-id>
KALSHI_PRIVATE_KEY_PATH=C:\absolute\path\to\kalshi-private-key.pem
```

The app signs read-only requests with RSA-PSS. It does not place orders.

## Install Dependencies

Python:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r api\requirements.txt
```

Web:

```powershell
cd web
npm.cmd install
cd ..
```

## Start Local Services

Initialize the Supabase database tables:

```powershell
.\scripts\init-db.ps1
```

If you created tables before decimal quantities were added, run this one-time migration:

```powershell
.\scripts\migrate-decimal-quantities.ps1
```

If you created tables before Kalshi sync was added, run this one-time migration:

```powershell
.\scripts\migrate-kalshi-fills.ps1
```

Terminal 1:

```powershell
.\scripts\start-api.ps1
```

Terminal 2:

```powershell
.\scripts\start-web.ps1
```

URLs:

- Web app: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Optional Docker Setup

Docker Compose is still available if you want local Postgres later:

```powershell
docker compose up --build
```

## Primary Workflow

1. Sync Kalshi activity from `/settings/kalshi`.
2. Review imported markets and positions.
3. Open `/needs-forecast` and add forecasts for imported positions that need your probability and thesis.
4. Add forecast updates as your view changes.
5. Let Kalshi sync provide fills, fees, positions, settlements, and account snapshots.
6. Export CSV files for deeper analysis.

Manual market and trade entry exists only as fallback. Kalshi should be treated as the source of truth for buys, sells, fees, settlements, and account data.

## Kalshi Sync

After configuring `KALSHI_ACCESS_KEY` and `KALSHI_PRIVATE_KEY_PATH`, start the API and web app, then open:

```text
http://localhost:3000/settings/kalshi
```

Use `Sync Kalshi` to pull recent fills, orders, settlements, and current position snapshots. Leave ticker blank for recent activity, or provide one ticker to filter fills/orders/settlements.

The sync pipeline:

- Stores raw Kalshi source records first.
- Converts fills into executions.
- Converts settlements into outcomes and forecast scores.
- Keeps forecasts, thesis, and reviews manual.
- Shows reconciliation counts for unconverted records and imported positions missing forecasts.

## Backend Tests

```powershell
cd api
..\.venv\Scripts\python.exe -m pytest
```
