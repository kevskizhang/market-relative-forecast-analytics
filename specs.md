# Market-Relative Forecast Analytics Specification

## 1. Project Purpose

Market-Relative Forecast Analytics is a personal prediction-market journal and analytics app. It records subjective forecasts, market-implied probabilities, trades, exits, outcomes, and postmortems so forecast quality and trade execution can be evaluated separately.

The central product principle is:

> Forecast lifecycle and position lifecycle are separate.

A user can make forecasts without trading, trade without changing a forecast, update probabilities over time, close a position before market resolution, and later evaluate both forecast accuracy and trading performance.

## 2. Core Concepts

### Markets

A market is the prediction-market question or event being tracked.

Examples:

- "Will Candidate A win the election?"
- "Will inflation be above 3% by June 30?"
- "Will Company X announce an acquisition before year end?"

Markets contain descriptive metadata, platform details, resolution criteria, status, and final outcome.

### Market Snapshots

A market snapshot records the market state at a specific point in time. Snapshots are used to preserve changing market-implied probabilities rather than overwriting them.

All internal probability comparisons should normalize to YES probability.

Example:

- YES price of 0.44 implies market probability of 44%.
- NO price of 0.40 implies YES probability of 60%.

### Forecasts

A forecast is the user's subjective probability estimate for a market at a specific time.

Forecasts are snapshot-based. Updating a probability creates a new forecast record instead of modifying the old one.

Forecasts support analysis of calibration, market-relative accuracy, edge decay, and whether the user continued holding a position after the original edge disappeared.

### Positions

A position is the user's financial exposure in a market.

Positions track side, status, size, cost basis, realized P&L, unrealized P&L, fees, and lifecycle state. Positions should not be used as a substitute for forecasts.

### Executions

An execution is an individual buy or sell fill.

Executions are the source of truth for position accounting. Average entry price, remaining quantity, realized P&L, and cost basis should be computed from executions rather than manually stored as the only record.

### Outcomes

An outcome records final market resolution and payout behavior.

Outcomes enable forecast scoring and final position settlement. Voided or ambiguous outcomes may be excluded from forecast-accuracy metrics while still preserving actual trade P&L.

### Postmortems

A postmortem is a structured review after a position closes or market resolves.

Postmortems separate forecast errors from trade execution errors and capture process lessons, mistake tags, and qualitative reasoning.

## 3. Primary User Workflows

### Create a Market and Paper Forecast

The user creates a market, enters the current market price, and records a subjective probability estimate without opening a real position.

Required behavior:

- Create a market record.
- Create a market snapshot.
- Create a forecast record.
- Compute edge as user probability minus market probability.
- Allow the forecast to remain pending until market resolution.

### Open a Real Position

The user records a trade after or alongside a forecast.

Required behavior:

- Create or select an existing market.
- Record the current market snapshot.
- Record the user's forecast.
- Create a position.
- Create the initial execution.
- Link the position to the relevant forecast when available.
- Compute expected value per share, max loss, total exposure, and edge after fees where possible.

### Update a Forecast

The user revises their probability estimate as new information arrives.

Required behavior:

- Create a new market snapshot.
- Create a new forecast record.
- Preserve previous forecasts.
- Mark prior forecast as superseded if using forecast statuses.
- Show previous edge, current edge, and any open exposure.
- Flag important state changes such as edge disappeared, edge reversed, thesis changed, or invalidation triggered.

### Add to a Position

The user increases exposure in an existing position.

Required behavior:

- Add a new execution.
- Recompute average entry, quantity, cost basis, max loss, and exposure.
- Prompt for or require an updated forecast before adding size.
- Preserve whether the user added after a loss, added without new information, or added after edge changed.

### Partially Close a Position

The user sells or reduces part of an existing position before resolution.

Required behavior:

- Add a sell execution.
- Recompute remaining quantity and cost basis.
- Compute realized P&L on the closed portion.
- Set position status to partially closed when exposure remains.
- Capture exit reason.

### Fully Close Before Resolution

The user exits the full position before the market resolves.

Required behavior:

- Add final sell execution.
- Set position status to closed before resolution.
- Treat trade P&L as final.
- Keep forecast status pending until market resolution.
- Upon later resolution, compare actual P&L against hypothetical hold-to-resolution P&L.

### Resolve a Market

The user records the final outcome.

Required behavior:

- Set final outcome and resolution timestamp.
- Set market status to resolved, voided, ambiguous, or cancelled as appropriate.
- Compute forecast scores for eligible forecasts.
- Settle any open positions.
- Compute final P&L.
- Trigger review status when applicable.

### Review a Market or Position

The user records a postmortem after resolution or position close.

Required behavior:

- Capture whether the thesis played out.
- Capture forecast error reason.
- Capture trade error reason.
- Capture execution, sizing, and exit quality.
- Capture process score, mistake tags, lesson, and notes.
- Compare actual trade result with hold-to-resolution result when relevant.

## 4. Data Model

### markets

Represents a prediction-market event or question.

Fields:

- id
- platform
- platform_market_id
- market_url
- title
- description
- category
- sub_category
- resolution_criteria
- yes_contract_name
- no_contract_name
- created_at
- expected_resolution_date
- actual_resolution_date
- status
- final_outcome
- notes

Status values:

- open
- resolved
- voided
- ambiguous
- cancelled

Final outcome values:

- YES
- NO
- VOID
- AMBIGUOUS

### market_snapshots

Represents market price and liquidity at a point in time.

Fields:

- id
- market_id
- timestamp
- market_probability_yes
- yes_bid
- yes_ask
- yes_mid
- no_bid
- no_ask
- no_mid
- last_trade_price
- volume
- open_interest
- spread
- liquidity_notes
- source

MVP fields:

- market_id
- timestamp
- market_probability_yes
- bid
- ask
- spread
- source

### forecasts

Represents the user's subjective probability estimate at a point in time.

Fields:

- id
- market_id
- market_snapshot_id
- timestamp
- forecast_probability_yes
- market_probability_yes
- edge
- confidence
- thesis
- invalidation_criteria
- information_sources
- research_quality
- forecast_type
- status
- notes

Research quality values:

- low
- medium
- high

Forecast type values:

- initial
- update
- pre_trade
- post_news
- pre_resolution

Forecast status values:

- active
- superseded
- resolved_scored
- excluded

### positions

Represents financial exposure in a market.

Fields:

- id
- market_id
- linked_forecast_id
- side
- status
- opened_at
- closed_at
- quantity
- average_entry_price
- average_exit_price
- initial_cost
- remaining_cost_basis
- realized_pnl
- unrealized_pnl
- total_pnl
- fees
- max_loss
- position_notes

Side values:

- YES
- NO

Status values:

- open
- partially_closed
- closed_before_resolution
- resolved
- voided

### executions

Represents an individual buy or sell fill.

Fields:

- id
- position_id
- market_id
- timestamp
- action
- side
- price
- quantity
- fees
- order_type
- reason
- notes

Action values:

- buy
- sell

Order type values:

- market
- limit
- manual

### outcomes

Represents final market resolution and payout terms.

Fields:

- id
- market_id
- resolved_at
- final_outcome
- payout_per_yes_share
- payout_per_no_share
- include_in_stats
- resolution_notes

Default payout behavior:

- YES outcome: YES pays 1.00, NO pays 0.00.
- NO outcome: YES pays 0.00, NO pays 1.00.
- VOID outcome: payout is platform-specific.

### postmortems

Represents structured review after closing or resolution.

Fields:

- id
- market_id
- position_id
- reviewed_at
- did_thesis_play_out
- forecast_error_reason
- trade_error_reason
- execution_quality
- sizing_quality
- exit_quality
- process_score
- mistake_tags
- lesson
- notes

Forecast error reason values:

- bad_base_rate
- missed_information
- overweighted_news
- underweighted_market
- bad_assumption
- random_outcome
- not_applicable

Trade error reason values:

- bad_entry
- bad_exit
- oversized
- undersized
- ignored_invalidation
- chased
- spread_too_wide
- fees_too_high
- emotional_trade
- not_applicable

Mistake tag examples:

- overconfident
- no_clear_edge
- low_research_quality
- ignored_exit_rule
- held_after_edge_disappeared
- held_after_edge_reversed
- sold_too_early
- averaged_down_without_new_info
- chased_price
- spread_erased_edge
- too_close_to_resolution
- voided_market

## 5. Screen Requirements

### Markets

Purpose:

- List, search, filter, create, and inspect tracked markets.

Core fields:

- title
- platform
- market_url
- category
- status
- expected_resolution_date
- final_outcome

### Market Detail

Purpose:

- Show one market's full timeline.

Required sections:

- Market metadata
- Latest market snapshot
- Forecast history
- Open or closed positions
- Executions
- Outcome
- Postmortem
- Flags and review prompts

### New Market

Required fields:

- title
- platform
- market_url
- category
- resolution_criteria
- expected_resolution_date

Optional fields:

- description
- sub_category
- notes

### New Forecast

Required fields:

- market_id
- timestamp
- market_probability_yes
- forecast_probability_yes
- thesis
- confidence

Strongly recommended fields:

- invalidation_criteria
- research_quality
- information_sources

Computed fields:

- edge
- absolute_edge

### New Position

Required fields:

- market_id
- side
- entry_price
- quantity
- opened_at

Strongly recommended fields:

- fees
- order_type
- linked_forecast_id
- reason_for_trade

Computed fields:

- cost
- max_loss
- expected_value_per_share
- total_expected_value
- edge_after_fees

### Add Execution

Required fields:

- position_id
- action
- side
- price
- quantity
- timestamp

Optional fields:

- fees
- order_type
- reason
- notes

Computed fields:

- new_average_entry
- realized_pnl
- remaining_quantity
- remaining_cost_basis

### Resolve Market

Required fields:

- market_id
- final_outcome
- resolved_at

Optional fields:

- resolution_notes
- include_in_stats

Computed fields:

- forecast_scores
- final_position_pnl
- hypothetical_hold_pnl

### Postmortem

Required fields:

- did_thesis_play_out
- process_score
- lesson

Strongly recommended fields:

- forecast_error_reason
- trade_error_reason
- execution_quality
- sizing_quality
- exit_quality
- mistake_tags

## 6. Computed Metrics

### Forecast Metrics

For eligible resolved forecasts:

```text
brier_user = (forecast_probability_yes - outcome)^2
brier_market = (market_probability_yes - outcome)^2
brier_improvement = brier_market - brier_user
```

Where:

```text
outcome = 1 for YES
outcome = 0 for NO
```

Positive Brier improvement means the user's forecast beat the market baseline.

### Trade Metrics

For each position:

- realized_pnl
- unrealized_pnl
- total_pnl
- return_on_cost
- max_loss
- position_size
- holding_period
- average_entry
- average_exit

For positions closed before resolution:

```text
early_exit_value_added = actual_pnl - hypothetical_hold_to_resolution_pnl
```

Positive early exit value means exiting before resolution helped. Negative early exit value means exiting reduced returns compared with holding.

### Edge Metrics

At each forecast:

```text
edge = forecast_probability_yes - market_probability_yes
```

For YES positions:

```text
expected_value_per_share = forecast_probability_yes - entry_price
```

For NO positions:

```text
expected_value_per_share = (1 - forecast_probability_yes) - entry_price
```

Potential flags:

- edge_positive
- edge_negative
- edge_disappeared
- edge_reversed
- edge_large
- edge_small
- market_moved_against_user
- market_moved_in_user_favor
- thesis_changed
- invalidation_triggered

### Behavioral Metrics

Track process behaviors over time:

- followed_exit_rule
- added_after_loss
- added_without_new_forecast
- sold_before_resolution
- held_after_edge_reversed
- trade_without_thesis
- trade_without_invalidation
- oversized_trade
- reviewed_trade

## 7. Dashboard Requirements

The dashboard should summarize forecasting, trading, process, and exposure.

### Forecasting

- number of forecasts
- resolved forecasts
- average Brier score
- average market Brier score
- average Brier improvement

### Trading

- total P&L
- realized P&L
- unrealized P&L
- win rate
- average trade size

### Process

- percent of trades with thesis
- percent of trades with invalidation criteria
- percent of adds with forecast update first
- percent of closed or resolved trades reviewed

### Exposure

- current open exposure
- largest position
- exposure by category
- markets resolving soon

## 8. MVP Scope

### MVP Must Include

- Kalshi as the first explicitly modeled prediction-market platform.
- Create and edit markets.
- Add market snapshots manually.
- Add forecast snapshots.
- Open positions.
- Add buy and sell executions.
- Partially and fully close positions.
- Resolve markets.
- Compute Brier score.
- Compute market-relative Brier improvement.
- Compute position P&L.
- Compare actual P&L with hold-to-resolution P&L for early exits.
- Track bankroll or account equity snapshots.
- Provide a basic dashboard.
- Export data to CSV.
- Include a methodology or README page explaining the scoring model.

### MVP Can Defer

- Automatic prediction-market data ingestion.
- Advanced behavioral analytics.
- LLM-based thesis analysis.
- Complex bankroll modeling.
- Options or multi-leg instruments.
- Multi-outcome markets.
- Automated trading recommendations.
- Mobile-specific polish.

## 9. Design and Product Constraints

- MVP supports binary YES/NO markets only.
- Kalshi is the first supported platform; other platforms should not drive MVP schema complexity unless the abstraction is cheap.
- Monetary values should be stored as integer minor units, such as cents, rather than floating-point dollars.
- Forecast records must be immutable snapshots.
- Executions must be preserved as individual records.
- Position summary values should be derived from executions when practical.
- Forecast accuracy and trade P&L must be reported separately.
- Voided markets should be excluded from calibration and Brier statistics by default.
- Ambiguous markets should be excluded from forecast accuracy metrics by default unless explicitly included.
- Adding to an existing position requires a new forecast update first.
- The app may flag inconsistencies, but it should not provide automated trading advice.
- Process metrics should be emphasized early, before there is enough resolved data for performance metrics to be meaningful.

## 10. Bankroll Tracking

The MVP should track bankroll or account equity over time so position size, exposure, and returns can be analyzed relative to available capital.

### bankroll_snapshots

Represents account value at a point in time.

Fields:

- id
- timestamp
- platform
- cash_balance_minor_units
- open_position_value_minor_units
- total_equity_minor_units
- notes

Required uses:

- Compute position size as a percentage of bankroll.
- Track total exposure relative to bankroll.
- Track changes in account equity over time.
- Provide context for whether trades were oversized or undersized.

Bankroll tracking can be manual in the MVP. Automatic account sync can be deferred.

## 11. Resolved Product Decisions

- MVP platform: Kalshi.
- MVP market type: binary YES/NO markets.
- Money storage: integer minor units.
- Adding to an existing position: requires a fresh forecast update.
- Bankroll tracking: included in MVP as manual account-equity snapshots.

## 12. Open Questions

- Should market snapshots be purely manual at first, or should the architecture include import hooks from day one?
- Should Kalshi fees be entered manually per execution, estimated by the app, or both?
- Should bankroll snapshots be entered manually, imported from CSV, or both?
