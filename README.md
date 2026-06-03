# Market-Relative Forecast Analytics

Personal Kalshi forecast and trade journal for logging binary prediction markets, subjective probabilities, executions, outcomes, bankroll snapshots, and market-relative scoring.

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

## Manual Logging Flow

1. Add a bankroll snapshot.
2. Create a market.
3. Add a market snapshot and forecast.
4. Open a position from the forecast.
5. Add forecast updates as your view changes.
6. Add buy/sell executions from the position detail page.
7. Resolve the market when Kalshi resolves it.
8. Export CSV files for analysis.

## Backend Tests

```powershell
cd api
..\.venv\Scripts\python.exe -m pytest
```
