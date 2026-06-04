from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Market(Base):
    __tablename__ = "markets"
    __table_args__ = (
        CheckConstraint("status in ('open', 'resolved', 'voided', 'ambiguous', 'cancelled')"),
        CheckConstraint("final_outcome is null or final_outcome in ('YES', 'NO', 'VOID', 'AMBIGUOUS')"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String, nullable=False, default="kalshi")
    platform_market_id: Mapped[str | None] = mapped_column(String)
    market_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String, nullable=False)
    sub_category: Mapped[str | None] = mapped_column(String)
    resolution_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    yes_contract_name: Mapped[str] = mapped_column(String, nullable=False, default="YES")
    no_contract_name: Mapped[str] = mapped_column(String, nullable=False, default="NO")
    expected_resolution_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_resolution_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    final_outcome: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)

    snapshots: Mapped[list[MarketSnapshot]] = relationship(back_populates="market", cascade="all, delete-orphan")
    forecasts: Mapped[list[Forecast]] = relationship(back_populates="market", cascade="all, delete-orphan")
    positions: Mapped[list[Position]] = relationship(back_populates="market", cascade="all, delete-orphan")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (
        CheckConstraint("market_probability_yes_bps between 0 and 10000"),
        CheckConstraint("spread_bps is null or spread_bps >= 0"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    market_probability_yes_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    yes_bid_bps: Mapped[int | None] = mapped_column(Integer)
    yes_ask_bps: Mapped[int | None] = mapped_column(Integer)
    yes_mid_bps: Mapped[int | None] = mapped_column(Integer)
    no_bid_bps: Mapped[int | None] = mapped_column(Integer)
    no_ask_bps: Mapped[int | None] = mapped_column(Integer)
    no_mid_bps: Mapped[int | None] = mapped_column(Integer)
    last_trade_price_bps: Mapped[int | None] = mapped_column(Integer)
    volume: Mapped[int | None] = mapped_column(Integer)
    open_interest: Mapped[int | None] = mapped_column(Integer)
    spread_bps: Mapped[int | None] = mapped_column(Integer)
    liquidity_notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)

    market: Mapped[Market] = relationship(back_populates="snapshots")


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        CheckConstraint("forecast_probability_yes_bps between 0 and 10000"),
        CheckConstraint("market_probability_yes_bps between 0 and 10000"),
        CheckConstraint("confidence between 1 and 5"),
        CheckConstraint("research_quality is null or research_quality in ('low', 'medium', 'high')"),
        CheckConstraint("forecast_type in ('initial', 'update', 'pre_trade', 'post_news', 'pre_resolution')"),
        CheckConstraint("status in ('active', 'superseded', 'resolved_scored', 'excluded')"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    market_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("market_snapshots.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    forecast_probability_yes_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    market_probability_yes_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    edge_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    invalidation_criteria: Mapped[str | None] = mapped_column(Text)
    information_sources: Mapped[str | None] = mapped_column(Text)
    research_quality: Mapped[str | None] = mapped_column(String)
    forecast_type: Mapped[str] = mapped_column(String, nullable=False, default="initial")
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)

    market: Mapped[Market] = relationship(back_populates="forecasts")


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (
        CheckConstraint("side in ('YES', 'NO')"),
        CheckConstraint("status in ('open', 'partially_closed', 'closed_before_resolution', 'resolved', 'voided')"),
        CheckConstraint("quantity >= 0"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    linked_forecast_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("forecasts.id"))
    side: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal("0"))
    average_entry_price_bps: Mapped[int | None] = mapped_column(Integer)
    average_exit_price_bps: Mapped[int | None] = mapped_column(Integer)
    initial_cost_minor_units: Mapped[int | None] = mapped_column(Integer)
    remaining_cost_basis_minor_units: Mapped[int | None] = mapped_column(Integer)
    realized_pnl_minor_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unrealized_pnl_minor_units: Mapped[int | None] = mapped_column(Integer)
    total_pnl_minor_units: Mapped[int | None] = mapped_column(Integer)
    fees_minor_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_loss_minor_units: Mapped[int | None] = mapped_column(Integer)
    position_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)

    market: Mapped[Market] = relationship(back_populates="positions")
    executions: Mapped[list[Execution]] = relationship(back_populates="position", cascade="all, delete-orphan")


class Execution(Base):
    __tablename__ = "executions"
    __table_args__ = (
        CheckConstraint("action in ('buy', 'sell')"),
        CheckConstraint("side in ('YES', 'NO')"),
        CheckConstraint("price_bps between 0 and 10000"),
        CheckConstraint("quantity > 0"),
        CheckConstraint("fees_minor_units >= 0"),
        CheckConstraint("order_type in ('market', 'limit', 'manual')"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kalshi_fill_id: Mapped[str | None] = mapped_column(String, unique=True)
    position_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    action: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    price_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    fees_minor_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    order_type: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)

    position: Mapped[Position] = relationship(back_populates="executions")


class KalshiFill(Base):
    __tablename__ = "kalshi_fills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fill_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    order_id: Mapped[str | None] = mapped_column(String)
    trade_id: Mapped[str | None] = mapped_column(String)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    market_ticker: Mapped[str | None] = mapped_column(String)
    action: Mapped[str | None] = mapped_column(String)
    side: Mapped[str | None] = mapped_column(String)
    count: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    yes_price_bps: Mapped[int | None] = mapped_column(Integer)
    no_price_bps: Mapped[int | None] = mapped_column(Integer)
    fee_minor_units: Mapped[int | None] = mapped_column(Integer)
    created_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    imported_execution_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("executions.id"))
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class KalshiOrder(Base):
    __tablename__ = "kalshi_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str | None] = mapped_column(String)
    side: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    order_type: Mapped[str | None] = mapped_column(String)
    initial_count: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    fill_count: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    remaining_count: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    yes_price_bps: Mapped[int | None] = mapped_column(Integer)
    no_price_bps: Mapped[int | None] = mapped_column(Integer)
    created_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class KalshiSettlement(Base):
    __tablename__ = "kalshi_settlements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    settlement_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    event_ticker: Mapped[str | None] = mapped_column(String)
    market_result: Mapped[str | None] = mapped_column(String)
    yes_count: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    no_count: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    revenue_minor_units: Mapped[int | None] = mapped_column(Integer)
    value_minor_units: Mapped[int | None] = mapped_column(Integer)
    fee_minor_units: Mapped[int | None] = mapped_column(Integer)
    settled_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    imported_outcome_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("outcomes.id"))
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class KalshiPositionSnapshot(Base):
    __tablename__ = "kalshi_position_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    yes_count: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    no_count: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    market_exposure_minor_units: Mapped[int | None] = mapped_column(Integer)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class KalshiBalanceSnapshot(Base):
    __tablename__ = "kalshi_balance_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    balance_minor_units: Mapped[int | None] = mapped_column(Integer)
    portfolio_value_minor_units: Mapped[int | None] = mapped_column(Integer)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class KalshiDeposit(Base):
    __tablename__ = "kalshi_deposits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deposit_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[str | None] = mapped_column(String)
    deposit_type: Mapped[str | None] = mapped_column(String)
    amount_minor_units: Mapped[int | None] = mapped_column(Integer)
    fee_minor_units: Mapped[int | None] = mapped_column(Integer)
    created_ts: Mapped[int | None] = mapped_column(Integer)
    finalized_ts: Mapped[int | None] = mapped_column(Integer)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class KalshiWithdrawal(Base):
    __tablename__ = "kalshi_withdrawals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    withdrawal_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[str | None] = mapped_column(String)
    withdrawal_type: Mapped[str | None] = mapped_column(String)
    amount_minor_units: Mapped[int | None] = mapped_column(Integer)
    fee_minor_units: Mapped[int | None] = mapped_column(Integer)
    created_ts: Mapped[int | None] = mapped_column(Integer)
    finalized_ts: Mapped[int | None] = mapped_column(Integer)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class Outcome(Base):
    __tablename__ = "outcomes"
    __table_args__ = (
        CheckConstraint("final_outcome in ('YES', 'NO', 'VOID', 'AMBIGUOUS')"),
        CheckConstraint("payout_per_yes_share_bps between 0 and 10000"),
        CheckConstraint("payout_per_no_share_bps between 0 and 10000"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False, unique=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    final_outcome: Mapped[str] = mapped_column(String, nullable=False)
    payout_per_yes_share_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    payout_per_no_share_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    include_in_stats: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class ForecastScore(Base):
    __tablename__ = "forecast_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forecast_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("forecasts.id"), nullable=False, unique=True)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    outcome_value_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    brier_user_bps_squared: Mapped[int] = mapped_column(Integer, nullable=False)
    brier_market_bps_squared: Mapped[int] = mapped_column(Integer, nullable=False)
    brier_improvement_bps_squared: Mapped[int] = mapped_column(Integer, nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class Postmortem(Base):
    __tablename__ = "postmortems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    position_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("positions.id"))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    did_thesis_play_out: Mapped[bool | None] = mapped_column(Boolean)
    forecast_error_reason: Mapped[str | None] = mapped_column(String)
    trade_error_reason: Mapped[str | None] = mapped_column(String)
    execution_quality: Mapped[int | None] = mapped_column(Integer)
    sizing_quality: Mapped[int | None] = mapped_column(Integer)
    exit_quality: Mapped[int | None] = mapped_column(Integer)
    process_score: Mapped[int] = mapped_column(Integer, nullable=False)
    mistake_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    lesson: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class BankrollSnapshot(Base):
    __tablename__ = "bankroll_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    platform: Mapped[str] = mapped_column(String, nullable=False, default="kalshi")
    cash_balance_minor_units: Mapped[int] = mapped_column(Integer, nullable=False)
    open_position_value_minor_units: Mapped[int] = mapped_column(Integer, nullable=False)
    total_equity_minor_units: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
