from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import calculations as calc
from .models import (
    BankrollSnapshot,
    Execution,
    Forecast,
    ForecastScore,
    Market,
    MarketSnapshot,
    Outcome,
    Position,
    Postmortem,
    now_utc,
)
from .schemas import (
    BankrollSnapshotCreate,
    ExecutionCreate,
    ForecastCreate,
    MarketCreate,
    OutcomeCreate,
    PositionCreate,
    PostmortemCreate,
    SnapshotCreate,
)


def require_market(db: Session, market_id: uuid.UUID) -> Market:
    market = db.get(Market, market_id)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    return market


def require_position(db: Session, position_id: uuid.UUID) -> Position:
    position = db.get(Position, position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return position


def create_market(db: Session, data: MarketCreate) -> Market:
    market = Market(**data.model_dump(), platform="kalshi", status="open")
    db.add(market)
    db.commit()
    db.refresh(market)
    return market


def create_snapshot(db: Session, market_id: uuid.UUID, data: SnapshotCreate) -> MarketSnapshot:
    require_market(db, market_id)
    if data.yes_bid_bps is not None and data.yes_ask_bps is not None and data.yes_ask_bps < data.yes_bid_bps:
        raise HTTPException(status_code=400, detail="YES ask must be greater than or equal to YES bid")
    spread = data.yes_ask_bps - data.yes_bid_bps if data.yes_bid_bps is not None and data.yes_ask_bps is not None else None
    mid = round((data.yes_bid_bps + data.yes_ask_bps) / 2) if data.yes_bid_bps is not None and data.yes_ask_bps is not None else None
    snapshot = MarketSnapshot(
        market_id=market_id,
        timestamp=data.timestamp or now_utc(),
        market_probability_yes_bps=data.market_probability_yes_bps,
        yes_bid_bps=data.yes_bid_bps,
        yes_ask_bps=data.yes_ask_bps,
        yes_mid_bps=mid,
        last_trade_price_bps=data.last_trade_price_bps,
        volume=data.volume,
        open_interest=data.open_interest,
        spread_bps=spread,
        liquidity_notes=data.liquidity_notes,
        source=data.source,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def create_forecast(db: Session, market_id: uuid.UUID, data: ForecastCreate) -> Forecast:
    require_market(db, market_id)
    for active in db.scalars(select(Forecast).where(Forecast.market_id == market_id, Forecast.status == "active")):
        active.status = "superseded"
    forecast = Forecast(
        market_id=market_id,
        market_snapshot_id=data.market_snapshot_id,
        timestamp=data.timestamp or now_utc(),
        forecast_probability_yes_bps=data.forecast_probability_yes_bps,
        market_probability_yes_bps=data.market_probability_yes_bps,
        edge_bps=calc.edge_bps(data.forecast_probability_yes_bps, data.market_probability_yes_bps),
        confidence=data.confidence,
        thesis=data.thesis,
        invalidation_criteria=data.invalidation_criteria,
        information_sources=data.information_sources,
        research_quality=data.research_quality,
        forecast_type=data.forecast_type,
        status="active",
        notes=data.notes,
    )
    db.add(forecast)
    db.commit()
    db.refresh(forecast)
    return forecast


def _require_forecast(db: Session, forecast_id: uuid.UUID, market_id: uuid.UUID) -> Forecast:
    forecast = db.get(Forecast, forecast_id)
    if not forecast or forecast.market_id != market_id:
        raise HTTPException(status_code=400, detail="Linked forecast does not belong to this market")
    return forecast


def open_position(db: Session, data: PositionCreate) -> Position:
    require_market(db, data.market_id)
    forecast = _require_forecast(db, data.linked_forecast_id, data.market_id)
    if data.side not in ("YES", "NO"):
        raise HTTPException(status_code=400, detail="Position side must be YES or NO")
    opened_at = data.opened_at or now_utc()
    cost = calc.buy_cost_minor_units(data.quantity, data.entry_price_bps, data.fees_minor_units)
    position = Position(
        market_id=data.market_id,
        linked_forecast_id=forecast.id,
        side=data.side,
        status="open",
        opened_at=opened_at,
        quantity=data.quantity,
        average_entry_price_bps=data.entry_price_bps,
        initial_cost_minor_units=cost,
        remaining_cost_basis_minor_units=cost,
        fees_minor_units=data.fees_minor_units,
        max_loss_minor_units=cost,
        position_notes=data.notes,
    )
    db.add(position)
    db.flush()
    execution = Execution(
        position_id=position.id,
        market_id=data.market_id,
        timestamp=opened_at,
        action="buy",
        side=data.side,
        price_bps=data.entry_price_bps,
        quantity=data.quantity,
        fees_minor_units=data.fees_minor_units,
        order_type=data.order_type,
        reason=data.reason,
        notes=data.notes,
    )
    db.add(execution)
    db.commit()
    db.refresh(position)
    return position


def _latest_execution_time(position: Position) -> datetime:
    if not position.executions:
        return position.opened_at
    return max(execution.timestamp for execution in position.executions)


def add_execution(db: Session, position_id: uuid.UUID, data: ExecutionCreate) -> Execution:
    position = require_position(db, position_id)
    if position.status not in ("open", "partially_closed"):
        raise HTTPException(status_code=400, detail="Cannot add executions to a closed position")
    if data.side != position.side:
        raise HTTPException(status_code=400, detail="Execution side must match position side")
    if data.action not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="Action must be buy or sell")

    timestamp = data.timestamp or now_utc()
    if data.action == "buy":
        if not data.linked_forecast_id:
            raise HTTPException(status_code=400, detail="Adding size requires a fresh linked forecast")
        forecast = _require_forecast(db, data.linked_forecast_id, position.market_id)
        if forecast.timestamp <= _latest_execution_time(position):
            raise HTTPException(status_code=400, detail="Linked forecast must be newer than the latest execution")

    if data.action == "sell" and data.quantity > position.quantity:
        raise HTTPException(status_code=400, detail="Sell quantity cannot exceed current position quantity")

    execution = Execution(
        position_id=position.id,
        market_id=position.market_id,
        timestamp=timestamp,
        action=data.action,
        side=data.side,
        price_bps=data.price_bps,
        quantity=data.quantity,
        fees_minor_units=data.fees_minor_units,
        order_type=data.order_type,
        reason=data.reason,
        notes=data.notes,
    )
    db.add(execution)
    _apply_execution_to_position(position, execution)
    position.updated_at = now_utc()
    db.commit()
    db.refresh(execution)
    return execution


def _apply_execution_to_position(position: Position, execution: Execution) -> None:
    remaining_cost = position.remaining_cost_basis_minor_units or 0
    total_fees = position.fees_minor_units + execution.fees_minor_units

    if execution.action == "buy":
        cost = calc.buy_cost_minor_units(execution.quantity, execution.price_bps, execution.fees_minor_units)
        previous_quantity = position.quantity
        position.quantity += execution.quantity
        position.remaining_cost_basis_minor_units = remaining_cost + cost
        position.max_loss_minor_units = (position.max_loss_minor_units or 0) + cost
        position.average_entry_price_bps = calc.average_price_bps(position.remaining_cost_basis_minor_units, position.quantity)
        if position.initial_cost_minor_units is None:
            position.initial_cost_minor_units = cost
        elif previous_quantity == 0:
            position.initial_cost_minor_units += cost
        position.status = "open"

    if execution.action == "sell":
        proceeds = calc.sell_proceeds_minor_units(execution.quantity, execution.price_bps, execution.fees_minor_units)
        cost_basis_sold = round(remaining_cost * execution.quantity / position.quantity)
        position.realized_pnl_minor_units += proceeds - cost_basis_sold
        position.quantity -= execution.quantity
        position.remaining_cost_basis_minor_units = remaining_cost - cost_basis_sold
        position.average_exit_price_bps = execution.price_bps
        position.status = "closed_before_resolution" if position.quantity == 0 else "partially_closed"
        if position.quantity == 0:
            position.closed_at = execution.timestamp
            position.total_pnl_minor_units = position.realized_pnl_minor_units

    position.fees_minor_units = total_fees


def resolve_market(db: Session, market_id: uuid.UUID, data: OutcomeCreate) -> Outcome:
    market = require_market(db, market_id)
    if db.scalar(select(Outcome).where(Outcome.market_id == market_id)):
        raise HTTPException(status_code=400, detail="Market is already resolved")
    final = data.final_outcome
    if final not in ("YES", "NO", "VOID", "AMBIGUOUS"):
        raise HTTPException(status_code=400, detail="Invalid final outcome")
    include = data.include_in_stats
    if include is None:
        include = final in ("YES", "NO")
    payout_yes = 10000 if final == "YES" else 0
    payout_no = 10000 if final == "NO" else 0
    if final in ("VOID", "AMBIGUOUS"):
        payout_yes = 0
        payout_no = 0

    outcome = Outcome(
        market_id=market_id,
        resolved_at=data.resolved_at or now_utc(),
        final_outcome=final,
        payout_per_yes_share_bps=payout_yes,
        payout_per_no_share_bps=payout_no,
        include_in_stats=include,
        resolution_notes=data.resolution_notes,
    )
    db.add(outcome)
    market.final_outcome = final
    market.actual_resolution_date = outcome.resolved_at.date()
    market.status = {"YES": "resolved", "NO": "resolved", "VOID": "voided", "AMBIGUOUS": "ambiguous"}[final]
    market.updated_at = now_utc()

    if include and final in ("YES", "NO"):
        for forecast in db.scalars(select(Forecast).where(Forecast.market_id == market_id)):
            outcome_bps, user, market_score, improvement = calc.brier_scores_bps_squared(
                forecast.forecast_probability_yes_bps,
                forecast.market_probability_yes_bps,
                final,
            )
            db.add(
                ForecastScore(
                    forecast_id=forecast.id,
                    market_id=market_id,
                    outcome_value_bps=outcome_bps,
                    brier_user_bps_squared=user,
                    brier_market_bps_squared=market_score,
                    brier_improvement_bps_squared=improvement,
                )
            )
            forecast.status = "resolved_scored"

    for position in db.scalars(select(Position).where(Position.market_id == market_id)):
        if position.status in ("open", "partially_closed"):
            payout_bps = payout_yes if position.side == "YES" else payout_no
            payout = calc.contract_value_minor_units(position.quantity, payout_bps)
            position.total_pnl_minor_units = position.realized_pnl_minor_units + payout - (position.remaining_cost_basis_minor_units or 0)
            position.unrealized_pnl_minor_units = None
            position.remaining_cost_basis_minor_units = 0
            position.quantity = 0
            position.status = "voided" if final == "VOID" else "resolved"
            position.closed_at = outcome.resolved_at
            position.updated_at = now_utc()

    db.commit()
    db.refresh(outcome)
    return outcome


def create_bankroll_snapshot(db: Session, data: BankrollSnapshotCreate) -> BankrollSnapshot:
    total = data.total_equity_minor_units
    if total is None:
        total = data.cash_balance_minor_units + data.open_position_value_minor_units
    snapshot = BankrollSnapshot(
        timestamp=data.timestamp or now_utc(),
        platform=data.platform,
        cash_balance_minor_units=data.cash_balance_minor_units,
        open_position_value_minor_units=data.open_position_value_minor_units,
        total_equity_minor_units=total,
        notes=data.notes,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def create_postmortem(db: Session, data: PostmortemCreate) -> Postmortem:
    require_market(db, data.market_id)
    if data.position_id:
        require_position(db, data.position_id)
    postmortem = Postmortem(**data.model_dump())
    db.add(postmortem)
    db.commit()
    db.refresh(postmortem)
    return postmortem

