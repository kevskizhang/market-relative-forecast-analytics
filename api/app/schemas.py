from __future__ import annotations

import uuid
from datetime import date, datetime

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
    quantity: int = Field(gt=0)
    fees_minor_units: int = Field(default=0, ge=0)
    order_type: str = "manual"
    reason: str | None = None
    notes: str | None = None


class PositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    market_id: uuid.UUID
    linked_forecast_id: uuid.UUID | None = None
    side: str
    status: str
    opened_at: datetime
    closed_at: datetime | None = None
    quantity: int
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


class ExecutionCreate(BaseModel):
    timestamp: datetime | None = None
    action: str
    side: str
    price_bps: int = Field(ge=0, le=10000)
    quantity: int = Field(gt=0)
    fees_minor_units: int = Field(default=0, ge=0)
    order_type: str = "manual"
    reason: str | None = None
    notes: str | None = None
    linked_forecast_id: uuid.UUID | None = None


class ExecutionRead(ExecutionCreate):
    model_config = ConfigDict(from_attributes=True)

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

