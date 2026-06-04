from __future__ import annotations

import uuid
import json
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import calculations as calc
from . import kalshi
from .models import (
    BankrollSnapshot,
    Execution,
    Forecast,
    ForecastScore,
    KalshiBalanceSnapshot,
    KalshiDeposit,
    KalshiFill,
    KalshiOrder,
    KalshiPositionSnapshot,
    KalshiSettlement,
    KalshiWithdrawal,
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
    ForecastUpdate,
    MarketCreate,
    MarketUpdate,
    OutcomeCreate,
    PositionCreate,
    PositionUpdate,
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


def update_market(db: Session, market_id: uuid.UUID, data: MarketUpdate) -> Market:
    market = require_market(db, market_id)
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(market, key, value)
    market.updated_at = now_utc()
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


def create_kalshi_snapshot(db: Session, market_id: uuid.UUID) -> MarketSnapshot:
    market = require_market(db, market_id)
    if not market.platform_market_id:
        raise HTTPException(status_code=400, detail="Market does not have a Kalshi ticker")
    kalshi_market = kalshi.search_market(market.platform_market_id)
    probability = kalshi_market.get("market_probability_yes_bps")
    if probability is None:
        raise HTTPException(status_code=400, detail="Kalshi response did not include a usable YES price")
    return create_snapshot(
        db,
        market_id,
        SnapshotCreate(
            market_probability_yes_bps=probability,
            yes_bid_bps=kalshi_market.get("yes_bid_bps"),
            yes_ask_bps=kalshi_market.get("yes_ask_bps"),
            last_trade_price_bps=kalshi_market.get("last_trade_price_bps"),
            volume=kalshi_market.get("volume"),
            open_interest=kalshi_market.get("open_interest"),
            source="kalshi",
        ),
    )


def import_kalshi_market(db: Session, ticker: str) -> Market:
    kalshi_market = kalshi.search_market(ticker)
    existing = db.scalar(select(Market).where(Market.platform == "kalshi", Market.platform_market_id == kalshi_market["ticker"]))
    if existing:
        return update_market_from_kalshi(db, existing.id)
    market = Market(
        platform="kalshi",
        platform_market_id=kalshi_market["ticker"],
        market_url=kalshi_market["market_url"],
        title=kalshi_market["title"],
        description=kalshi_market.get("description"),
        category=kalshi_market["category"],
        resolution_criteria=kalshi_market["resolution_criteria"],
        expected_resolution_date=_date_or_today(kalshi_market.get("expected_resolution_date")),
        status="open",
    )
    db.add(market)
    db.flush()
    if kalshi_market.get("market_probability_yes_bps") is not None:
        create_snapshot(
            db,
            market.id,
            SnapshotCreate(
                market_probability_yes_bps=kalshi_market["market_probability_yes_bps"],
                yes_bid_bps=kalshi_market.get("yes_bid_bps"),
                yes_ask_bps=kalshi_market.get("yes_ask_bps"),
                last_trade_price_bps=kalshi_market.get("last_trade_price_bps"),
                volume=kalshi_market.get("volume"),
                open_interest=kalshi_market.get("open_interest"),
                source="kalshi",
            ),
        )
    else:
        db.commit()
    db.refresh(market)
    return market


def update_market_from_kalshi(db: Session, market_id: uuid.UUID) -> Market:
    market = require_market(db, market_id)
    if not market.platform_market_id:
        raise HTTPException(status_code=400, detail="Market does not have a Kalshi ticker")
    kalshi_market = kalshi.search_market(market.platform_market_id)
    market.platform_market_id = kalshi_market["ticker"]
    market.market_url = kalshi_market["market_url"]
    market.title = kalshi_market["title"]
    market.description = kalshi_market.get("description")
    market.category = kalshi_market["category"]
    market.resolution_criteria = kalshi_market["resolution_criteria"]
    if kalshi_market.get("expected_resolution_date"):
        market.expected_resolution_date = _date_or_today(kalshi_market["expected_resolution_date"])
    market.updated_at = now_utc()
    db.commit()
    db.refresh(market)
    return market


def _date_or_today(value: str | None):
    if not value:
        return now_utc().date()
    return datetime.fromisoformat(value).date()


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


def require_forecast(db: Session, forecast_id: uuid.UUID) -> Forecast:
    forecast = db.get(Forecast, forecast_id)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    return forecast


def update_forecast(db: Session, forecast_id: uuid.UUID, data: ForecastUpdate) -> Forecast:
    forecast = require_forecast(db, forecast_id)
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(forecast, key, value)
    forecast.edge_bps = calc.edge_bps(forecast.forecast_probability_yes_bps, forecast.market_probability_yes_bps)
    db.execute(delete(ForecastScore).where(ForecastScore.forecast_id == forecast.id))
    db.commit()
    db.refresh(forecast)
    return forecast


def delete_forecast(db: Session, forecast_id: uuid.UUID) -> None:
    forecast = require_forecast(db, forecast_id)
    for position in db.scalars(select(Position).where(Position.linked_forecast_id == forecast.id)):
        position.linked_forecast_id = None
    db.execute(delete(ForecastScore).where(ForecastScore.forecast_id == forecast.id))
    db.delete(forecast)
    db.commit()


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


def update_position(db: Session, position_id: uuid.UUID, data: PositionUpdate) -> Position:
    position = require_position(db, position_id)
    updates = data.model_dump(exclude_unset=True)
    if "linked_forecast_id" in updates and updates["linked_forecast_id"] is not None:
        _require_forecast(db, updates["linked_forecast_id"], position.market_id)
    for key, value in updates.items():
        setattr(position, key, value)
    position.updated_at = now_utc()
    db.commit()
    db.refresh(position)
    return position


def delete_position(db: Session, position_id: uuid.UUID) -> None:
    position = require_position(db, position_id)
    db.execute(delete(Execution).where(Execution.position_id == position.id))
    db.execute(delete(Postmortem).where(Postmortem.position_id == position.id))
    db.delete(position)
    db.commit()


def import_kalshi_fills(
    db: Session,
    ticker: str | None = None,
    min_ts: int | None = None,
    max_ts: int | None = None,
) -> dict[str, int]:
    fills = kalshi.get_fills(ticker=ticker, min_ts=min_ts, max_ts=max_ts)
    return _store_and_convert_kalshi_fills(db, fills)


def sync_kalshi_activity(
    db: Session,
    ticker: str | None = None,
    min_ts: int | None = None,
    max_ts: int | None = None,
    include_historical: bool = False,
) -> dict[str, int]:
    fills = kalshi.get_fills(ticker=ticker, min_ts=min_ts, max_ts=max_ts)
    if include_historical:
        fills.extend(kalshi.get_historical_fills(ticker=ticker, min_ts=min_ts, max_ts=max_ts))
    fill_result = _store_and_convert_kalshi_fills(db, fills)
    order_result = _store_kalshi_orders(db, kalshi.get_orders(ticker=ticker, min_ts=min_ts, max_ts=max_ts))
    settlement_result = _store_and_convert_kalshi_settlements(db, kalshi.get_settlements(ticker=ticker, min_ts=min_ts, max_ts=max_ts))
    position_result = _store_kalshi_position_snapshots(db, kalshi.get_positions())
    balance_result = _store_kalshi_balance(db, kalshi.get_balance())
    deposit_result = _store_kalshi_deposits(db, kalshi.get_deposits())
    withdrawal_result = _store_kalshi_withdrawals(db, kalshi.get_withdrawals())
    return {
        "fills_received": fill_result["received"],
        "fills_stored": fill_result["stored"],
        "fills_converted": fill_result["converted"],
        "fills_skipped": fill_result["skipped"],
        "orders_received": order_result["received"],
        "orders_stored": order_result["stored"],
        "orders_skipped": order_result["skipped"],
        "settlements_received": settlement_result["received"],
        "settlements_stored": settlement_result["stored"],
        "settlements_converted": settlement_result["converted"],
        "settlements_skipped": settlement_result["skipped"],
        "position_snapshots_received": position_result["received"],
        "position_snapshots_stored": position_result["stored"],
        "position_snapshots_skipped": position_result["skipped"],
        "balance_snapshots_stored": balance_result["stored"],
        "deposits_received": deposit_result["received"],
        "deposits_stored": deposit_result["stored"],
        "deposits_skipped": deposit_result["skipped"],
        "withdrawals_received": withdrawal_result["received"],
        "withdrawals_stored": withdrawal_result["stored"],
        "withdrawals_skipped": withdrawal_result["skipped"],
    }


def rebuild_kalshi_derived_records(db: Session) -> dict[str, int]:
    imported_position_ids = {
        row[0]
        for row in db.execute(
            select(Position.id).where(Position.position_notes.ilike("%Imported from Kalshi%"))
        )
    }
    imported_position_ids.update(
        row[0]
        for row in db.execute(
            select(Execution.position_id).where(Execution.kalshi_fill_id.is_not(None))
        )
    )

    forecast_by_market_side: dict[tuple[uuid.UUID, str], uuid.UUID] = {}
    if imported_position_ids:
        for position in db.scalars(select(Position).where(Position.id.in_(imported_position_ids))):
            if position.linked_forecast_id:
                forecast_by_market_side[(position.market_id, position.side)] = position.linked_forecast_id

    deleted_positions = 0
    deleted_executions = 0
    if imported_position_ids:
        deleted_executions += db.execute(delete(Execution).where(Execution.position_id.in_(imported_position_ids))).rowcount or 0
        deleted_positions += db.execute(delete(Position).where(Position.id.in_(imported_position_ids))).rowcount or 0
    deleted_executions += db.execute(delete(Execution).where(Execution.kalshi_fill_id.is_not(None))).rowcount or 0

    db.execute(delete(ForecastScore))
    for fill in db.scalars(select(KalshiFill)):
        fill.imported_execution_id = None

    imported_outcome_ids = [row[0] for row in db.execute(select(KalshiSettlement.imported_outcome_id).where(KalshiSettlement.imported_outcome_id.is_not(None)))]
    for settlement in db.scalars(select(KalshiSettlement).where(KalshiSettlement.imported_outcome_id.is_not(None))):
        settlement.imported_outcome_id = None
    db.flush()
    if imported_outcome_ids:
        db.execute(delete(Outcome).where(Outcome.id.in_(imported_outcome_ids)))

    for market in db.scalars(select(Market).where(Market.platform == "kalshi")):
        market.status = "open"
        market.final_outcome = None
        market.actual_resolution_date = None
        market.updated_at = now_utc()
    for forecast in db.scalars(select(Forecast).where(Forecast.status == "resolved_scored")):
        forecast.status = "active"

    converted_fills = convert_unconverted_kalshi_fills(db)
    for position in db.scalars(select(Position).where(Position.linked_forecast_id.is_(None))):
        linked = forecast_by_market_side.get((position.market_id, position.side))
        if linked:
            position.linked_forecast_id = linked
    converted_settlements = convert_unconverted_kalshi_settlements(db)
    reconcile_positions_with_latest_kalshi_snapshot(db)
    db.commit()
    return {
        "deleted_positions": deleted_positions,
        "deleted_executions": deleted_executions,
        "converted_fills": converted_fills,
        "converted_settlements": converted_settlements,
    }


def _store_and_convert_kalshi_fills(db: Session, fills: list[dict[str, object]]) -> dict[str, int]:
    stored = 0
    skipped = 0
    for raw_fill in sorted(fills, key=lambda fill: str(fill.get("created_time") or "")):
        fill_id = str(raw_fill.get("fill_id") or "")
        if not fill_id:
            skipped += 1
            continue
        existing = db.scalar(select(KalshiFill).where(KalshiFill.fill_id == fill_id))
        if existing:
            skipped += 1
            continue
        normalized = _normalize_kalshi_fill(raw_fill)
        fill = KalshiFill(**normalized, raw_json=json.dumps(raw_fill, sort_keys=True, default=str))
        db.add(fill)
        db.flush()
        stored += 1
    converted = convert_unconverted_kalshi_fills(db)
    db.commit()
    return {"received": len(fills), "stored": stored, "converted": converted, "skipped": skipped}


def convert_unconverted_kalshi_fills(db: Session) -> int:
    converted = 0
    fills = list(
        db.scalars(
            select(KalshiFill)
            .where(KalshiFill.imported_execution_id.is_(None))
            .order_by(KalshiFill.created_time.asc().nulls_last(), KalshiFill.imported_at.asc())
        )
    )
    for fill in fills:
        existing_execution = db.scalar(select(Execution).where(Execution.kalshi_fill_id == fill.fill_id))
        if existing_execution:
            fill.imported_execution_id = existing_execution.id
            continue
        execution = _convert_kalshi_fill_to_execution(db, fill)
        if execution:
            fill.imported_execution_id = execution.id
            converted += 1
    return converted


def _store_kalshi_orders(db: Session, orders: list[dict[str, object]]) -> dict[str, int]:
    stored = 0
    skipped = 0
    for raw_order in orders:
        order_id = str(raw_order.get("order_id") or "")
        if not order_id:
            skipped += 1
            continue
        if db.scalar(select(KalshiOrder).where(KalshiOrder.order_id == order_id)):
            skipped += 1
            continue
        order = KalshiOrder(**_normalize_kalshi_order(raw_order), raw_json=json.dumps(raw_order, sort_keys=True, default=str))
        db.add(order)
        stored += 1
    db.commit()
    return {"received": len(orders), "stored": stored, "skipped": skipped}


def _store_and_convert_kalshi_settlements(db: Session, settlements: list[dict[str, object]]) -> dict[str, int]:
    stored = 0
    skipped = 0
    for raw_settlement in sorted(settlements, key=lambda settlement: str(settlement.get("settled_time") or "")):
        normalized = _normalize_kalshi_settlement(raw_settlement)
        settlement_key = str(normalized["settlement_key"])
        if db.scalar(select(KalshiSettlement).where(KalshiSettlement.settlement_key == settlement_key)):
            skipped += 1
            continue
        db.add(KalshiSettlement(**normalized, raw_json=json.dumps(raw_settlement, sort_keys=True, default=str)))
        stored += 1
    converted = convert_unconverted_kalshi_settlements(db)
    db.commit()
    return {"received": len(settlements), "stored": stored, "converted": converted, "skipped": skipped}


def convert_unconverted_kalshi_settlements(db: Session) -> int:
    converted = 0
    settlements = list(
        db.scalars(
            select(KalshiSettlement)
            .where(KalshiSettlement.imported_outcome_id.is_(None))
            .order_by(KalshiSettlement.settled_time.asc().nulls_last(), KalshiSettlement.imported_at.asc())
        )
    )
    for settlement in settlements:
        outcome = _convert_kalshi_settlement_to_outcome(db, settlement)
        if outcome:
            settlement.imported_outcome_id = outcome.id
            converted += 1
    return converted


def _store_kalshi_position_snapshots(db: Session, positions: list[dict[str, object]]) -> dict[str, int]:
    stored = 0
    skipped = 0
    imported_at = now_utc()
    for raw_position in positions:
        ticker = str(raw_position.get("ticker") or raw_position.get("market_ticker") or "").upper()
        if not ticker:
            skipped += 1
            continue
        snapshot_key = f"{ticker}:{int(imported_at.timestamp() * 1000)}"
        if db.scalar(select(KalshiPositionSnapshot).where(KalshiPositionSnapshot.snapshot_key == snapshot_key)):
            skipped += 1
            continue
        snapshot = KalshiPositionSnapshot(
            snapshot_key=snapshot_key,
            ticker=ticker,
            position=_decimal_or_none(raw_position.get("position_fp") or raw_position.get("position")),
            yes_count=_decimal_or_none(raw_position.get("yes_count_fp") or raw_position.get("yes_count")),
            no_count=_decimal_or_none(raw_position.get("no_count_fp") or raw_position.get("no_count")),
            market_exposure_minor_units=_dollars_to_cents(raw_position.get("market_exposure_dollars") or raw_position.get("market_exposure")),
            raw_json=json.dumps(raw_position, sort_keys=True, default=str),
            imported_at=imported_at,
        )
        db.add(snapshot)
        stored += 1
    db.commit()
    return {"received": len(positions), "stored": stored, "skipped": skipped}


def _store_kalshi_balance(db: Session, raw_balance: dict[str, object]) -> dict[str, int]:
    balance_minor_units = _first_present_minor_units(raw_balance, "balance", "balance_cents", "cash_balance", "available_balance")
    portfolio_value_minor_units = _first_present_minor_units(raw_balance, "portfolio_value", "portfolio_value_cents", "total_value", "total_balance")
    snapshot = KalshiBalanceSnapshot(
        balance_minor_units=balance_minor_units,
        portfolio_value_minor_units=portfolio_value_minor_units,
        raw_json=json.dumps(raw_balance, sort_keys=True, default=str),
    )
    db.add(snapshot)
    if balance_minor_units is not None:
        db.add(
            BankrollSnapshot(
                platform="kalshi",
                cash_balance_minor_units=max(balance_minor_units, 0),
                open_position_value_minor_units=max((portfolio_value_minor_units or balance_minor_units) - balance_minor_units, 0),
                total_equity_minor_units=max(portfolio_value_minor_units or balance_minor_units, 0),
                notes="Imported from Kalshi balance",
            )
        )
    db.commit()
    return {"stored": 1}


def _store_kalshi_deposits(db: Session, deposits: list[dict[str, object]]) -> dict[str, int]:
    stored = 0
    skipped = 0
    for raw in deposits:
        deposit_id = str(raw.get("id") or raw.get("deposit_id") or "")
        if not deposit_id:
            skipped += 1
            continue
        if db.scalar(select(KalshiDeposit).where(KalshiDeposit.deposit_id == deposit_id)):
            skipped += 1
            continue
        db.add(
            KalshiDeposit(
                deposit_id=deposit_id,
                status=raw.get("status"),
                deposit_type=raw.get("type"),
                amount_minor_units=_first_present_minor_units(raw, "amount_cents", "amount"),
                fee_minor_units=_first_present_minor_units(raw, "fee_cents", "fee"),
                created_ts=_int_or_none(raw.get("created_ts")),
                finalized_ts=_int_or_none(raw.get("finalized_ts")),
                raw_json=json.dumps(raw, sort_keys=True, default=str),
            )
        )
        stored += 1
    db.commit()
    return {"received": len(deposits), "stored": stored, "skipped": skipped}


def _store_kalshi_withdrawals(db: Session, withdrawals: list[dict[str, object]]) -> dict[str, int]:
    stored = 0
    skipped = 0
    for raw in withdrawals:
        withdrawal_id = str(raw.get("id") or raw.get("withdrawal_id") or "")
        if not withdrawal_id:
            skipped += 1
            continue
        if db.scalar(select(KalshiWithdrawal).where(KalshiWithdrawal.withdrawal_id == withdrawal_id)):
            skipped += 1
            continue
        db.add(
            KalshiWithdrawal(
                withdrawal_id=withdrawal_id,
                status=raw.get("status"),
                withdrawal_type=raw.get("type"),
                amount_minor_units=_first_present_minor_units(raw, "amount_cents", "amount"),
                fee_minor_units=_first_present_minor_units(raw, "fee_cents", "fee"),
                created_ts=_int_or_none(raw.get("created_ts")),
                finalized_ts=_int_or_none(raw.get("finalized_ts")),
                raw_json=json.dumps(raw, sort_keys=True, default=str),
            )
        )
        stored += 1
    db.commit()
    return {"received": len(withdrawals), "stored": stored, "skipped": skipped}


def reconcile_positions_with_latest_kalshi_snapshot(db: Session) -> int:
    latest_snapshot_time = db.scalar(select(KalshiPositionSnapshot.imported_at).order_by(KalshiPositionSnapshot.imported_at.desc()).limit(1))
    if latest_snapshot_time is None:
        return 0
    latest_snapshots = list(
        db.scalars(select(KalshiPositionSnapshot).where(KalshiPositionSnapshot.imported_at == latest_snapshot_time))
    )
    open_by_ticker: dict[tuple[str, str], Decimal] = {}
    for snapshot in latest_snapshots:
        if snapshot.yes_count and snapshot.yes_count > 0:
            open_by_ticker[(snapshot.ticker, "YES")] = Decimal(snapshot.yes_count)
        if snapshot.no_count and snapshot.no_count > 0:
            open_by_ticker[(snapshot.ticker, "NO")] = Decimal(snapshot.no_count)
        if snapshot.position and snapshot.position != 0:
            side = "YES" if snapshot.position > 0 else "NO"
            open_by_ticker[(snapshot.ticker, side)] = abs(Decimal(snapshot.position))

    updated = 0
    positions = db.scalars(
        select(Position)
        .join(Market, Position.market_id == Market.id)
        .where(
            Market.platform == "kalshi",
            Position.status.in_(["open", "partially_closed"]),
            Position.position_notes.ilike("%Imported from Kalshi%"),
        )
    )
    for position in positions:
        ticker = position.market.platform_market_id
        if not ticker:
            continue
        expected_quantity = open_by_ticker.get((ticker, position.side), Decimal("0"))
        if expected_quantity == 0:
            position.status = "closed_before_resolution"
            position.closed_at = position.closed_at or latest_snapshot_time
            position.total_pnl_minor_units = position.realized_pnl_minor_units
            position.updated_at = now_utc()
            updated += 1
    return updated


def _normalize_kalshi_fill(raw_fill: dict[str, object]) -> dict[str, object]:
    ticker = str(raw_fill.get("ticker") or raw_fill.get("market_ticker") or "").upper()
    action = _normalize_action(raw_fill.get("action"))
    side = _normalize_side(raw_fill.get("side"))
    count = _decimal_or_none(raw_fill.get("count_fp") or raw_fill.get("count"))
    return {
        "fill_id": str(raw_fill.get("fill_id")),
        "order_id": raw_fill.get("order_id"),
        "trade_id": raw_fill.get("trade_id"),
        "ticker": ticker,
        "market_ticker": raw_fill.get("market_ticker"),
        "action": action,
        "side": side,
        "count": count,
        "yes_price_bps": _dollars_to_bps(raw_fill.get("yes_price_dollars")),
        "no_price_bps": _dollars_to_bps(raw_fill.get("no_price_dollars")),
        "fee_minor_units": _dollars_to_cents(raw_fill.get("fee_cost")),
        "created_time": _datetime_or_none(raw_fill.get("created_time")),
    }


def _normalize_kalshi_order(raw_order: dict[str, object]) -> dict[str, object]:
    ticker = str(raw_order.get("ticker") or raw_order.get("market_ticker") or "").upper()
    return {
        "order_id": str(raw_order.get("order_id")),
        "ticker": ticker,
        "action": _normalize_action(raw_order.get("action")),
        "side": _normalize_side(raw_order.get("side") or raw_order.get("outcome_side")),
        "status": raw_order.get("status"),
        "order_type": raw_order.get("type"),
        "initial_count": _decimal_or_none(raw_order.get("initial_count_fp") or raw_order.get("initial_count")),
        "fill_count": _decimal_or_none(raw_order.get("fill_count_fp") or raw_order.get("fill_count")),
        "remaining_count": _decimal_or_none(raw_order.get("remaining_count_fp") or raw_order.get("remaining_count")),
        "yes_price_bps": _dollars_to_bps(raw_order.get("yes_price_dollars")),
        "no_price_bps": _dollars_to_bps(raw_order.get("no_price_dollars")),
        "created_time": _datetime_or_none(raw_order.get("created_time")),
    }


def _normalize_kalshi_settlement(raw_settlement: dict[str, object]) -> dict[str, object]:
    ticker = str(raw_settlement.get("ticker") or raw_settlement.get("market_ticker") or "").upper()
    settled_time = _datetime_or_none(raw_settlement.get("settled_time"))
    settlement_key = f"{ticker}:{settled_time.isoformat() if settled_time else raw_settlement.get('ts') or raw_settlement.get('settled_time')}"
    return {
        "settlement_key": settlement_key,
        "ticker": ticker,
        "event_ticker": raw_settlement.get("event_ticker"),
        "market_result": _normalize_outcome(raw_settlement.get("market_result")),
        "yes_count": _decimal_or_none(raw_settlement.get("yes_count_fp") or raw_settlement.get("yes_count")),
        "no_count": _decimal_or_none(raw_settlement.get("no_count_fp") or raw_settlement.get("no_count")),
        "revenue_minor_units": _number_to_cents(raw_settlement.get("revenue")),
        "value_minor_units": _number_to_cents(raw_settlement.get("value")),
        "fee_minor_units": _dollars_to_cents(raw_settlement.get("fee_cost")),
        "settled_time": settled_time,
    }


def _convert_kalshi_fill_to_execution(db: Session, fill: KalshiFill) -> Execution | None:
    if not fill.ticker or not fill.count or not fill.action:
        return None
    fill_side = fill.side
    if fill_side not in ("YES", "NO"):
        return None

    market = db.scalar(select(Market).where(Market.platform == "kalshi", Market.platform_market_id == fill.ticker))
    if not market:
        try:
            market = import_kalshi_market(db, fill.ticker)
        except Exception:
            market = Market(
                platform="kalshi",
                platform_market_id=fill.ticker,
                market_url=f"https://kalshi.com/markets/{fill.ticker.lower()}",
                title=fill.ticker,
                category="Kalshi",
                resolution_criteria=fill.ticker,
                expected_resolution_date=(fill.created_time or now_utc()).date(),
                status="open",
            )
            db.add(market)
            db.flush()

    side = fill_side
    if fill.action == "sell":
        side = _execution_side_for_kalshi_sell(db, market.id, fill)
        if side is None:
            return None

    price_bps = _kalshi_price_bps_for_side(fill, side)
    if price_bps is None:
        return None

    position = _open_position_for_side(db, market.id, side)
    if not position:
        if fill.action == "sell":
            return None
        position = Position(
            market_id=market.id,
            side=side,
            status="open",
            opened_at=fill.created_time or now_utc(),
            quantity=Decimal("0"),
            realized_pnl_minor_units=0,
            fees_minor_units=0,
            position_notes="Imported from Kalshi fills. Attach a forecast manually.",
        )
        db.add(position)
        db.flush()

    if fill.action == "sell" and Decimal(fill.count) > Decimal(position.quantity):
        return None

    execution = Execution(
        kalshi_fill_id=fill.fill_id,
        position_id=position.id,
        market_id=market.id,
        timestamp=fill.created_time or now_utc(),
        action=fill.action,
        side=side,
        price_bps=price_bps,
        quantity=fill.count,
        fees_minor_units=fill.fee_minor_units or 0,
        order_type="manual",
        reason="Imported from Kalshi fill",
        notes=f"Kalshi fill {fill.fill_id}",
    )
    db.add(execution)
    db.flush()
    _apply_execution_to_position(position, execution)
    position.updated_at = now_utc()
    return execution


def _open_position_for_side(db: Session, market_id: uuid.UUID, side: str) -> Position | None:
    return db.scalar(
        select(Position).where(
            Position.market_id == market_id,
            Position.side == side,
            Position.status.in_(["open", "partially_closed"]),
        )
    )


def _opposite_binary_side(side: str) -> str:
    return "NO" if side == "YES" else "YES"


def _execution_side_for_kalshi_sell(db: Session, market_id: uuid.UUID, fill: KalshiFill) -> str | None:
    if fill.side not in ("YES", "NO"):
        return None
    opposite_side = _opposite_binary_side(fill.side)
    for side in (opposite_side, fill.side):
        position = _open_position_for_side(db, market_id, side)
        if position and Decimal(fill.count) <= Decimal(position.quantity):
            return side
    return None


def _kalshi_price_bps_for_side(fill: KalshiFill, side: str) -> int | None:
    if side == "YES":
        if fill.yes_price_bps is not None:
            return fill.yes_price_bps
        if fill.no_price_bps is not None:
            return 10000 - fill.no_price_bps
    if side == "NO":
        if fill.no_price_bps is not None:
            return fill.no_price_bps
        if fill.yes_price_bps is not None:
            return 10000 - fill.yes_price_bps
    return None


def _convert_kalshi_settlement_to_outcome(db: Session, settlement: KalshiSettlement) -> Outcome | None:
    if not settlement.ticker or settlement.market_result not in ("YES", "NO"):
        return None
    market = db.scalar(select(Market).where(Market.platform == "kalshi", Market.platform_market_id == settlement.ticker))
    if not market:
        try:
            market = import_kalshi_market(db, settlement.ticker)
        except Exception:
            market = Market(
                platform="kalshi",
                platform_market_id=settlement.ticker,
                market_url=f"https://kalshi.com/markets/{settlement.ticker.lower()}",
                title=settlement.ticker,
                category="Kalshi",
                resolution_criteria=settlement.ticker,
                expected_resolution_date=(settlement.settled_time or now_utc()).date(),
                status="open",
            )
            db.add(market)
            db.flush()

    existing = db.scalar(select(Outcome).where(Outcome.market_id == market.id))
    if existing:
        return existing
    outcome = Outcome(
        market_id=market.id,
        resolved_at=settlement.settled_time or now_utc(),
        final_outcome=settlement.market_result,
        payout_per_yes_share_bps=10000 if settlement.market_result == "YES" else 0,
        payout_per_no_share_bps=10000 if settlement.market_result == "NO" else 0,
        include_in_stats=True,
        resolution_notes=f"Imported from Kalshi settlement {settlement.settlement_key}",
    )
    db.add(outcome)
    market.final_outcome = settlement.market_result
    market.actual_resolution_date = outcome.resolved_at.date()
    market.status = "resolved"
    market.updated_at = now_utc()

    for forecast in db.scalars(select(Forecast).where(Forecast.market_id == market.id)):
        if db.scalar(select(ForecastScore).where(ForecastScore.forecast_id == forecast.id)):
            continue
        outcome_bps, user, market_score, improvement = calc.brier_scores_bps_squared(
            forecast.forecast_probability_yes_bps,
            forecast.market_probability_yes_bps,
            settlement.market_result,
        )
        db.add(
            ForecastScore(
                forecast_id=forecast.id,
                market_id=market.id,
                outcome_value_bps=outcome_bps,
                brier_user_bps_squared=user,
                brier_market_bps_squared=market_score,
                brier_improvement_bps_squared=improvement,
            )
        )
        forecast.status = "resolved_scored"

    for position in db.scalars(select(Position).where(Position.market_id == market.id, Position.status.in_(["open", "partially_closed"]))):
        payout_bps = outcome.payout_per_yes_share_bps if position.side == "YES" else outcome.payout_per_no_share_bps
        payout = calc.contract_value_minor_units(position.quantity, payout_bps)
        position.total_pnl_minor_units = position.realized_pnl_minor_units + payout - (position.remaining_cost_basis_minor_units or 0)
        position.remaining_cost_basis_minor_units = 0
        position.quantity = Decimal("0")
        position.status = "resolved"
        position.closed_at = outcome.resolved_at
        position.updated_at = now_utc()
    db.flush()
    return outcome


def _normalize_action(value: object) -> str | None:
    if value is None:
        return None
    lowered = str(value).lower()
    if lowered in ("buy", "sell"):
        return lowered
    return None


def _normalize_side(value: object) -> str | None:
    if value is None:
        return None
    upper = str(value).upper()
    if upper in ("YES", "NO"):
        return upper
    return None


def _normalize_outcome(value: object) -> str | None:
    if value is None:
        return None
    upper = str(value).upper()
    if upper in ("YES", "NO"):
        return upper
    return None


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _dollars_to_bps(value: object) -> int | None:
    if value is None:
        return None
    return int((Decimal(str(value)) * Decimal("10000")).to_integral_value())


def _dollars_to_cents(value: object) -> int | None:
    if value is None:
        return None
    return int((Decimal(str(value)) * Decimal("100")).to_integral_value())


def _number_to_cents(value: object) -> int | None:
    if value is None:
        return None
    decimal_value = Decimal(str(value))
    if abs(decimal_value) >= Decimal("1000") and decimal_value == decimal_value.to_integral_value():
        return int(decimal_value)
    return int((decimal_value * Decimal("100")).to_integral_value())


def _first_present_minor_units(raw: dict[str, object], *keys: str) -> int | None:
    for key in keys:
        if raw.get(key) is not None:
            if key.endswith("_cents") or key in {"balance", "portfolio_value", "cash_balance", "available_balance", "total_value", "total_balance", "revenue", "value"}:
                return _int_or_none(raw.get(key))
            return _number_to_cents(raw.get(key))
    return None


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _datetime_or_none(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=now_utc().tzinfo)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


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
        previous_quantity = Decimal(position.quantity)
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
        cost_basis_sold = round(Decimal(remaining_cost) * Decimal(execution.quantity) / Decimal(position.quantity))
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


def undo_market_resolution(db: Session, market_id: uuid.UUID) -> Market:
    market = require_market(db, market_id)
    outcome = db.scalar(select(Outcome).where(Outcome.market_id == market_id))
    if not outcome:
        raise HTTPException(status_code=404, detail="Market does not have a resolution to undo")

    db.execute(delete(ForecastScore).where(ForecastScore.market_id == market_id))
    for settlement in db.scalars(select(KalshiSettlement).where(KalshiSettlement.imported_outcome_id == outcome.id)):
        settlement.imported_outcome_id = None
    db.delete(outcome)

    for forecast in db.scalars(select(Forecast).where(Forecast.market_id == market_id, Forecast.status == "resolved_scored")):
        forecast.status = "active"

    for position in db.scalars(select(Position).where(Position.market_id == market_id, Position.status == "resolved")):
        executions = list(db.scalars(select(Execution).where(Execution.position_id == position.id).order_by(Execution.timestamp.asc())))
        _recompute_position_from_executions(position, executions)

    market.status = "open"
    market.final_outcome = None
    market.actual_resolution_date = None
    market.updated_at = now_utc()
    db.commit()
    db.refresh(market)
    return market


def _recompute_position_from_executions(position: Position, executions: list[Execution]) -> None:
    opened_at = position.opened_at
    linked_forecast_id = position.linked_forecast_id
    notes = position.position_notes
    position.quantity = Decimal("0")
    position.status = "open"
    position.opened_at = opened_at
    position.closed_at = None
    position.linked_forecast_id = linked_forecast_id
    position.average_entry_price_bps = None
    position.average_exit_price_bps = None
    position.initial_cost_minor_units = None
    position.remaining_cost_basis_minor_units = 0
    position.realized_pnl_minor_units = 0
    position.unrealized_pnl_minor_units = None
    position.total_pnl_minor_units = None
    position.fees_minor_units = 0
    position.max_loss_minor_units = 0
    position.position_notes = notes
    for execution in executions:
        _apply_execution_to_position(position, execution)
    position.updated_at = now_utc()


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
