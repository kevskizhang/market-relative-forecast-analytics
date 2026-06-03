from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text
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
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
    position_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    action: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    price_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    fees_minor_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    order_type: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)

    position: Mapped[Position] = relationship(back_populates="executions")


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

