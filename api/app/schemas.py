from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MarketCreate(BaseModel):
    platform_market_id: str | None = None
    market_url: str | None = None
    title: str
    description: str | None = None
    category: str
    sub_category: str | None = None
    resolution_criteria: str
    yes_contract_name: str = "YES"
    no_contract_name: str = "NO"
    expected_resolution_date: date
    notes: str | None = None


class MarketUpdate(BaseModel):
    platform_market_id: str | None = None
    market_url: str | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None
    sub_category: str | None = None
    resolution_criteria: str | None = None
    yes_contract_name: str | None = None
    no_contract_name: str | None = None
    expected_resolution_date: date | None = None
    notes: str | None = None


class MarketRead(MarketCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: str
    actual_resolution_date: date | None = None
    status: str
    final_outcome: str | None = None
    created_at: datetime
    updated_at: datetime


class SnapshotCreate(BaseModel):
    timestamp: datetime | None = None
    market_probability_yes_bps: int = Field(ge=0, le=10000)
    yes_bid_bps: int | None = Field(default=None, ge=0, le=10000)
    yes_ask_bps: int | None = Field(default=None, ge=0, le=10000)
    last_trade_price_bps: int | None = Field(default=None, ge=0, le=10000)
    volume: int | None = None
    open_interest: int | None = None
    liquidity_notes: str | None = None
    source: str = "manual"


class SnapshotRead(SnapshotCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    market_id: uuid.UUID
    timestamp: datetime
    yes_mid_bps: int | None = None
    spread_bps: int | None = None
    created_at: datetime


class KalshiMarketRead(BaseModel):
    ticker: str
    event_ticker: str | None = None
    title: str
    description: str | None = None
    category: str
    market_url: str
    resolution_criteria: str
    expected_resolution_date: str | None = None
    status: str | None = None
    yes_bid_bps: int | None = None
    yes_ask_bps: int | None = None
    last_trade_price_bps: int | None = None
    market_probability_yes_bps: int | None = None
    volume: int | None = None
    open_interest: int | None = None


class KalshiImportCreate(BaseModel):
    ticker: str


class KalshiFillImportCreate(BaseModel):
    ticker: str | None = None
    min_ts: int | None = None
    max_ts: int | None = None


class KalshiFillImportResult(BaseModel):
    received: int
    stored: int
    converted: int
    skipped: int


class KalshiSyncCreate(BaseModel):
    ticker: str | None = None
    min_ts: int | None = None
    max_ts: int | None = None
    include_historical: bool = False


class KalshiSyncResult(BaseModel):
    fills_received: int
    fills_stored: int
    fills_converted: int
    fills_skipped: int
    orders_received: int
    orders_stored: int
    orders_skipped: int
    settlements_received: int
    settlements_stored: int
    settlements_converted: int
    settlements_skipped: int
    position_snapshots_received: int
    position_snapshots_stored: int
    position_snapshots_skipped: int
    balance_snapshots_stored: int
    deposits_received: int
    deposits_stored: int
    deposits_skipped: int
    withdrawals_received: int
    withdrawals_stored: int
    withdrawals_skipped: int


class KalshiReconciliationRead(BaseModel):
    raw_fills: int
    unconverted_fills: int
    raw_orders: int
    raw_settlements: int
    unconverted_settlements: int
    raw_position_snapshots: int
    raw_balance_snapshots: int
    raw_deposits: int
    raw_withdrawals: int
    imported_positions_missing_forecast: int
    imported_open_positions: int
    resolved_markets_needing_review: int
    latest_raw_import_at: datetime | None = None
    latest_balance_snapshot_at: datetime | None = None


class KalshiRebuildResult(BaseModel):
    deleted_positions: int
    deleted_executions: int
    converted_fills: int
    converted_settlements: int


class ForecastCreate(BaseModel):
    timestamp: datetime | None = None
    market_snapshot_id: uuid.UUID | None = None
    forecast_probability_yes_bps: int = Field(ge=0, le=10000)
    market_probability_yes_bps: int = Field(ge=0, le=10000)
    confidence: int = Field(ge=1, le=5)
    thesis: str
    invalidation_criteria: str | None = None
    information_sources: str | None = None
    research_quality: str | None = None
    forecast_type: str = "initial"
    notes: str | None = None


class ForecastUpdate(BaseModel):
    timestamp: datetime | None = None
    market_snapshot_id: uuid.UUID | None = None
    forecast_probability_yes_bps: int | None = Field(default=None, ge=0, le=10000)
    market_probability_yes_bps: int | None = Field(default=None, ge=0, le=10000)
    confidence: int | None = Field(default=None, ge=1, le=5)
    thesis: str | None = None
    invalidation_criteria: str | None = None
    information_sources: str | None = None
    research_quality: str | None = None
    forecast_type: str | None = None
    notes: str | None = None


class ForecastRead(ForecastCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    market_id: uuid.UUID
    timestamp: datetime
    edge_bps: int
    status: str
    created_at: datetime


class PositionCreate(BaseModel):
    market_id: uuid.UUID
    linked_forecast_id: uuid.UUID
    side: str
    opened_at: datetime | None = None
    entry_price_bps: int = Field(ge=0, le=10000)
    quantity: Decimal = Field(gt=0)
    fees_minor_units: int = Field(default=0, ge=0)
    order_type: str = "manual"
    reason: str | None = None
    notes: str | None = None


class PositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_encoders={Decimal: float})

    id: uuid.UUID
    market_id: uuid.UUID
    linked_forecast_id: uuid.UUID | None = None
    side: str
    status: str
    opened_at: datetime
    closed_at: datetime | None = None
    quantity: Decimal
    average_entry_price_bps: int | None = None
    average_exit_price_bps: int | None = None
    initial_cost_minor_units: int | None = None
    remaining_cost_basis_minor_units: int | None = None
    realized_pnl_minor_units: int
    unrealized_pnl_minor_units: int | None = None
    total_pnl_minor_units: int | None = None
    fees_minor_units: int
    max_loss_minor_units: int | None = None
    position_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class PositionUpdate(BaseModel):
    linked_forecast_id: uuid.UUID | None = None
    opened_at: datetime | None = None
    position_notes: str | None = None


class ExecutionCreate(BaseModel):
    timestamp: datetime | None = None
    action: str
    side: str
    price_bps: int = Field(ge=0, le=10000)
    quantity: Decimal = Field(gt=0)
    fees_minor_units: int = Field(default=0, ge=0)
    order_type: str = "manual"
    reason: str | None = None
    notes: str | None = None
    linked_forecast_id: uuid.UUID | None = None


class ExecutionRead(ExecutionCreate):
    model_config = ConfigDict(from_attributes=True, json_encoders={Decimal: float})

    id: uuid.UUID
    position_id: uuid.UUID
    market_id: uuid.UUID
    timestamp: datetime
    created_at: datetime


class OutcomeCreate(BaseModel):
    resolved_at: datetime | None = None
    final_outcome: str
    include_in_stats: bool | None = None
    resolution_notes: str | None = None


class OutcomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    market_id: uuid.UUID
    resolved_at: datetime
    final_outcome: str
    payout_per_yes_share_bps: int
    payout_per_no_share_bps: int
    include_in_stats: bool
    resolution_notes: str | None = None
    created_at: datetime


class ForecastScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    forecast_id: uuid.UUID
    market_id: uuid.UUID
    outcome_value_bps: int
    brier_user_bps_squared: int
    brier_market_bps_squared: int
    brier_improvement_bps_squared: int
    scored_at: datetime


class BankrollSnapshotCreate(BaseModel):
    timestamp: datetime | None = None
    platform: str = "kalshi"
    cash_balance_minor_units: int = Field(ge=0)
    open_position_value_minor_units: int = Field(ge=0)
    total_equity_minor_units: int | None = Field(default=None, ge=0)
    notes: str | None = None


class BankrollSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    timestamp: datetime
    platform: str
    cash_balance_minor_units: int
    open_position_value_minor_units: int
    total_equity_minor_units: int
    notes: str | None = None
    created_at: datetime


class PostmortemCreate(BaseModel):
    market_id: uuid.UUID
    position_id: uuid.UUID | None = None
    did_thesis_play_out: bool | None = None
    forecast_error_reason: str | None = None
    trade_error_reason: str | None = None
    execution_quality: int | None = Field(default=None, ge=1, le=5)
    sizing_quality: int | None = Field(default=None, ge=1, le=5)
    exit_quality: int | None = Field(default=None, ge=1, le=5)
    process_score: int = Field(ge=1, le=5)
    mistake_tags: list[str] | None = None
    lesson: str
    notes: str | None = None


class PostmortemRead(PostmortemCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reviewed_at: datetime
    created_at: datetime
    updated_at: datetime
