# Market-Relative Forecast Analytics Engineering Specification

## 1. Technical Stack

The MVP uses:

- Next.js for the web application UI.
- Python for the backend API, domain logic, calculations, imports, exports, and tests around financial math.
- Supabase-hosted PostgreSQL for durable relational storage.

Recommended concrete choices:

- Next.js App Router with TypeScript.
- Python FastAPI backend.
- SQLAlchemy ORM or SQLAlchemy Core for database access.
- Alembic for database migrations.
- Pydantic for request and response validation.
- pytest for backend tests.
- Playwright for critical frontend workflow tests once the UI exists.

## 2. System Architecture

### Runtime Services

The app should run as two local services during development:

- `web`: Next.js application.
- `api`: Python FastAPI application.

Supabase Postgres runs as the shared persistence layer.

```text
Browser
  -> Next.js web app
  -> Python FastAPI API
  -> Supabase PostgreSQL
```

### Ownership Boundaries

Next.js owns:

- Page routing.
- Forms and client-side interaction.
- Tables, dashboards, charts, and detail views.
- Calling the Python API.
- Lightweight display formatting.

Python owns:

- Database schema and migrations.
- Validation of domain inputs.
- Forecast scoring.
- Position accounting.
- P&L calculations.
- Bankroll metrics.
- CSV import and export.
- Any future Kalshi API integration.

Postgres owns:

- Source-of-truth records.
- Foreign key integrity.
- Enum-like constraints.
- Timestamps and durable audit history.

## 3. Core Engineering Decisions

### MVP Product Decisions

- Platform: Kalshi first.
- Market type: binary YES/NO only.
- User model: single-user MVP.
- Forecasts: immutable snapshots.
- Executions: individual records, never collapsed into only averages.
- Money: integer minor units, stored as cents.
- Probabilities and prices: integer basis points.
- Adding to a position: requires a new forecast update first.
- Bankroll tracking: manual account-equity snapshots in MVP.
- Database hosting: Supabase Postgres for local development and initial use.

### Money Representation

Store money as integer cents:

```text
$4.50 -> 450
$0.07 -> 7
```

This avoids floating-point rounding errors in accounting.

### Probability and Price Representation

Store probabilities and contract prices as integer basis points:

```text
0.4400 -> 4400
44.00% -> 4400
1.0000 -> 10000
```

Benefits:

- No floating-point drift.
- Easy display as percentages or decimal prices.
- Supports Kalshi-style cent prices and more precise manual estimates.

All YES/NO comparison metrics normalize to YES probability.

## 4. Database Schema

Use UUID primary keys unless there is a strong reason to use integers. Store `created_at` and `updated_at` on mutable tables. Use `timestamptz` for timestamps.

### markets

Purpose: prediction-market event or question.

Columns:

- `id uuid primary key`
- `platform text not null default 'kalshi'`
- `platform_market_id text`
- `market_url text`
- `title text not null`
- `description text`
- `category text not null`
- `sub_category text`
- `resolution_criteria text not null`
- `yes_contract_name text default 'YES'`
- `no_contract_name text default 'NO'`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- `expected_resolution_date date not null`
- `actual_resolution_date date`
- `status text not null`
- `final_outcome text`
- `notes text`

Constraints:

- `status in ('open', 'resolved', 'voided', 'ambiguous', 'cancelled')`
- `final_outcome in ('YES', 'NO', 'VOID', 'AMBIGUOUS')` when not null
- `platform = 'kalshi'` for MVP

Indexes:

- `(status)`
- `(expected_resolution_date)`
- `(platform, platform_market_id)`

### market_snapshots

Purpose: market price and liquidity at a point in time.

Columns:

- `id uuid primary key`
- `market_id uuid not null references markets(id)`
- `timestamp timestamptz not null`
- `market_probability_yes_bps integer not null`
- `yes_bid_bps integer`
- `yes_ask_bps integer`
- `yes_mid_bps integer`
- `no_bid_bps integer`
- `no_ask_bps integer`
- `no_mid_bps integer`
- `last_trade_price_bps integer`
- `volume integer`
- `open_interest integer`
- `spread_bps integer`
- `liquidity_notes text`
- `source text not null default 'manual'`
- `created_at timestamptz not null`

Constraints:

- Probability and price bps values are between `0` and `10000`.
- `spread_bps >= 0` when present.

Indexes:

- `(market_id, timestamp desc)`
- `(source)`

### forecasts

Purpose: immutable user probability estimate at a point in time.

Columns:

- `id uuid primary key`
- `market_id uuid not null references markets(id)`
- `market_snapshot_id uuid references market_snapshots(id)`
- `timestamp timestamptz not null`
- `forecast_probability_yes_bps integer not null`
- `market_probability_yes_bps integer not null`
- `edge_bps integer not null`
- `confidence integer not null`
- `thesis text not null`
- `invalidation_criteria text`
- `information_sources text`
- `research_quality text`
- `forecast_type text not null`
- `status text not null`
- `notes text`
- `created_at timestamptz not null`

Constraints:

- `forecast_probability_yes_bps between 0 and 10000`
- `market_probability_yes_bps between 0 and 10000`
- `edge_bps = forecast_probability_yes_bps - market_probability_yes_bps`
- `confidence between 1 and 5`
- `research_quality in ('low', 'medium', 'high')` when not null
- `forecast_type in ('initial', 'update', 'pre_trade', 'post_news', 'pre_resolution')`
- `status in ('active', 'superseded', 'resolved_scored', 'excluded')`

Indexes:

- `(market_id, timestamp desc)`
- `(status)`

### positions

Purpose: financial exposure in a market.

Columns:

- `id uuid primary key`
- `market_id uuid not null references markets(id)`
- `linked_forecast_id uuid references forecasts(id)`
- `side text not null`
- `status text not null`
- `opened_at timestamptz not null`
- `closed_at timestamptz`
- `quantity integer not null default 0`
- `average_entry_price_bps integer`
- `average_exit_price_bps integer`
- `initial_cost_minor_units integer`
- `remaining_cost_basis_minor_units integer`
- `realized_pnl_minor_units integer not null default 0`
- `unrealized_pnl_minor_units integer`
- `total_pnl_minor_units integer`
- `fees_minor_units integer not null default 0`
- `max_loss_minor_units integer`
- `position_notes text`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

Constraints:

- `side in ('YES', 'NO')`
- `status in ('open', 'partially_closed', 'closed_before_resolution', 'resolved', 'voided')`
- Price bps values are between `0` and `10000` when present.
- Quantity is non-negative on the summary row.

Implementation note:

- Summary accounting fields may be cached for query speed, but executions remain the source of truth.

Indexes:

- `(market_id)`
- `(status)`
- `(opened_at desc)`

### executions

Purpose: individual buy and sell fills.

Columns:

- `id uuid primary key`
- `position_id uuid not null references positions(id)`
- `market_id uuid not null references markets(id)`
- `timestamp timestamptz not null`
- `action text not null`
- `side text not null`
- `price_bps integer not null`
- `quantity integer not null`
- `fees_minor_units integer not null default 0`
- `order_type text not null`
- `reason text`
- `notes text`
- `created_at timestamptz not null`

Constraints:

- `action in ('buy', 'sell')`
- `side in ('YES', 'NO')`
- `price_bps between 0 and 10000`
- `quantity > 0`
- `fees_minor_units >= 0`
- `order_type in ('market', 'limit', 'manual')`

Indexes:

- `(position_id, timestamp)`
- `(market_id, timestamp)`

### outcomes

Purpose: final market resolution and payout terms.

Columns:

- `id uuid primary key`
- `market_id uuid not null unique references markets(id)`
- `resolved_at timestamptz not null`
- `final_outcome text not null`
- `payout_per_yes_share_bps integer not null`
- `payout_per_no_share_bps integer not null`
- `include_in_stats boolean not null default true`
- `resolution_notes text`
- `created_at timestamptz not null`

Constraints:

- `final_outcome in ('YES', 'NO', 'VOID', 'AMBIGUOUS')`
- Payout bps values are between `0` and `10000`.
- `include_in_stats = false` by default for `VOID` and `AMBIGUOUS`.

### forecast_scores

Purpose: persisted scoring results for resolved forecasts.

Columns:

- `id uuid primary key`
- `forecast_id uuid not null unique references forecasts(id)`
- `market_id uuid not null references markets(id)`
- `outcome_value_bps integer not null`
- `brier_user_bps_squared integer not null`
- `brier_market_bps_squared integer not null`
- `brier_improvement_bps_squared integer not null`
- `scored_at timestamptz not null`

Notes:

- Store Brier scores in basis-points-squared units to avoid floats.
- Convert to decimal display values in the API response or frontend.

### postmortems

Purpose: structured review after close or resolution.

Columns:

- `id uuid primary key`
- `market_id uuid not null references markets(id)`
- `position_id uuid references positions(id)`
- `reviewed_at timestamptz not null`
- `did_thesis_play_out boolean`
- `forecast_error_reason text`
- `trade_error_reason text`
- `execution_quality integer`
- `sizing_quality integer`
- `exit_quality integer`
- `process_score integer not null`
- `mistake_tags text[]`
- `lesson text not null`
- `notes text`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

Constraints:

- Quality scores are between `1` and `5` when present.
- `process_score between 1 and 5`

### bankroll_snapshots

Purpose: account value at a point in time.

Columns:

- `id uuid primary key`
- `timestamp timestamptz not null`
- `platform text not null default 'kalshi'`
- `cash_balance_minor_units integer not null`
- `open_position_value_minor_units integer not null`
- `total_equity_minor_units integer not null`
- `notes text`
- `created_at timestamptz not null`

Constraints:

- Money values are non-negative.
- `total_equity_minor_units = cash_balance_minor_units + open_position_value_minor_units` unless manually overridden by an explicit future field.

Indexes:

- `(timestamp desc)`
- `(platform, timestamp desc)`

## 5. Calculation Rules

### Edge

```text
edge_bps = forecast_probability_yes_bps - market_probability_yes_bps
```

### Expected Value Per Share

For YES:

```text
ev_bps = forecast_probability_yes_bps - entry_price_bps
```

For NO:

```text
ev_bps = (10000 - forecast_probability_yes_bps) - entry_price_bps
```

### Brier Score

Outcome value:

```text
YES -> 10000
NO -> 0
```

Basis-points-squared form:

```text
brier_user_bps_squared = (forecast_probability_yes_bps - outcome_value_bps)^2
brier_market_bps_squared = (market_probability_yes_bps - outcome_value_bps)^2
brier_improvement_bps_squared = brier_market_bps_squared - brier_user_bps_squared
```

Display form:

```text
display_brier = brier_bps_squared / 100000000
```

### Buy Cost

```text
gross_cost_minor_units = round(quantity * price_bps / 10000 * 100)
total_cost_minor_units = gross_cost_minor_units + fees_minor_units
```

For Kalshi-style cent contracts, price entry may already be cent-like. Convert to bps at input boundaries and keep accounting in minor units.

### Sell Proceeds

```text
gross_proceeds_minor_units = round(quantity * price_bps / 10000 * 100)
net_proceeds_minor_units = gross_proceeds_minor_units - fees_minor_units
```

### Realized P&L

Use average-cost accounting for MVP:

```text
realized_pnl = sell_net_proceeds - cost_basis_of_sold_shares
```

The cost basis of sold shares is:

```text
remaining_cost_basis * sold_quantity / remaining_quantity_before_sale
```

### Resolution Payout

For a remaining YES position:

```text
payout = remaining_quantity * payout_per_yes_share_bps / 10000 * 100
```

For a remaining NO position:

```text
payout = remaining_quantity * payout_per_no_share_bps / 10000 * 100
```

Final P&L:

```text
total_pnl = realized_pnl + resolution_payout - remaining_cost_basis
```

### Early Exit Value

For positions closed before resolution:

```text
early_exit_value_added = actual_pnl - hypothetical_hold_to_resolution_pnl
```

Positive means the exit helped. Negative means holding would have been better.

### Position Size Percent

Use the latest bankroll snapshot at or before the position open time:

```text
position_size_percent = initial_cost_minor_units / total_equity_minor_units
```

## 6. API Surface

The API should be resource-oriented and keep calculation logic server-side.

### Markets

- `GET /markets`
- `POST /markets`
- `GET /markets/{market_id}`
- `PATCH /markets/{market_id}`
- `POST /markets/{market_id}/resolve`

### Market Snapshots

- `POST /markets/{market_id}/snapshots`
- `GET /markets/{market_id}/snapshots`

### Forecasts

- `POST /markets/{market_id}/forecasts`
- `GET /markets/{market_id}/forecasts`

Behavior:

- Creating a new forecast should mark the previous active forecast for the market as superseded.
- Forecasts remain immutable after creation except for status changes controlled by the backend.

### Positions and Executions

- `GET /positions`
- `POST /positions`
- `GET /positions/{position_id}`
- `POST /positions/{position_id}/executions`

Behavior:

- Opening a position creates the initial buy execution.
- Adding size requires a forecast timestamp newer than the latest execution for that position.
- Adding an execution recomputes cached position summary fields.

### Outcomes and Scores

- `POST /markets/{market_id}/resolve`
- `GET /markets/{market_id}/scores`

Behavior:

- Resolving a market creates an outcome.
- Eligible forecasts are scored.
- Open positions are settled.

### Bankroll

- `GET /bankroll-snapshots`
- `POST /bankroll-snapshots`

### Dashboard

- `GET /dashboard/summary`

Returns:

- Forecasting metrics.
- Trading metrics.
- Process metrics.
- Exposure metrics.

### Export

- `GET /exports/markets.csv`
- `GET /exports/forecasts.csv`
- `GET /exports/positions.csv`
- `GET /exports/executions.csv`
- `GET /exports/outcomes.csv`
- `GET /exports/postmortems.csv`
- `GET /exports/bankroll-snapshots.csv`

## 7. Next.js Route Map

Use dense, work-focused screens rather than a marketing-style landing page.

Routes:

- `/` dashboard
- `/markets` market list
- `/markets/new` create market
- `/markets/[id]` market detail
- `/markets/[id]/forecast/new` add forecast
- `/positions` position list
- `/positions/[id]` position detail
- `/positions/[id]/execution/new` add execution
- `/bankroll` bankroll snapshots
- `/review` markets and positions needing review
- `/settings/export` CSV export
- `/methodology` scoring and accounting methodology

## 8. Validation Rules

### Market Validation

- Title is required.
- Platform is required and must be `kalshi` for MVP.
- Resolution criteria is required.
- Expected resolution date is required.
- Market URL should be unique when present.

### Snapshot Validation

- Market probability is required.
- Probability and prices must be between 0% and 100%.
- Ask must be greater than or equal to bid when both are present.
- Spread is derived when bid and ask are present.

### Forecast Validation

- Forecast probability is required.
- Market probability is required.
- Thesis is required.
- Confidence is required and must be 1 to 5.
- Edge is derived server-side.

### Position Validation

- Position side is required.
- Entry price is required.
- Quantity must be positive.
- A linked forecast is strongly preferred for opening and required before adding size.
- Position side must match execution side in MVP.

### Execution Validation

- Action is required.
- Price is required.
- Quantity must be positive.
- Sell quantity cannot exceed current open quantity.
- Adding buy quantity to an existing position requires a newer forecast update.

### Resolution Validation

- Final outcome is required.
- Resolution timestamp is required.
- VOID and AMBIGUOUS outcomes default to `include_in_stats = false`.

## 9. Testing Strategy

Financial math and scoring need tests before UI polish.

### Unit Tests

Test Python calculation functions for:

- YES edge calculation.
- NO expected value calculation.
- Brier score and market-relative improvement.
- Buy cost with fees.
- Partial sell realized P&L.
- Full close before resolution.
- Resolution while holding YES.
- Resolution while holding NO.
- Voided market excluded from forecast scoring.
- Early exit value added.
- Position size as percent of bankroll.

### API Tests

Test:

- Create market.
- Create snapshot.
- Create forecast.
- Open position.
- Reject add-to-position without fresh forecast.
- Add execution after fresh forecast.
- Resolve market and generate scores.
- Export CSV endpoints return expected columns.

### Frontend Workflow Tests

Once the UI exists, cover:

- Create market -> add forecast -> open position.
- Add forecast update -> add execution.
- Partial close -> resolve -> review.
- Dashboard loads with populated metrics.

## 10. Initial Implementation Order

1. Scaffold Next.js app, Python API, and Postgres development setup.
2. Add Python project structure, database connection, SQLAlchemy models, and Alembic.
3. Implement migrations for core tables.
4. Implement calculation functions with unit tests.
5. Implement market, snapshot, and forecast API endpoints.
6. Implement position and execution API endpoints.
7. Implement resolution, scoring, and settlement endpoints.
8. Implement bankroll snapshot endpoints.
9. Build Next.js dashboard, market list, market detail, and forms.
10. Add CSV exports.
11. Add methodology page.
12. Add focused frontend workflow tests.

## 11. Open Engineering Questions

- Should local development use Docker Compose for Postgres, API, and web together?
- Should the Python API expose OpenAPI-generated TypeScript types to the Next.js app?
- Should CSV import be included with export in MVP, or deferred until after manual entry works?
- Should Kalshi fees be manually entered, estimated automatically, or both?
- Should market snapshots include an optional raw Kalshi payload field for future import debugging?
