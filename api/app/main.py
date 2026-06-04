from __future__ import annotations

import csv
import io
import os
import uuid

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
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
)
from . import kalshi
from .schemas import (
    BankrollSnapshotCreate,
    BankrollSnapshotRead,
    ExecutionCreate,
    ExecutionRead,
    ForecastCreate,
    ForecastRead,
    ForecastUpdate,
    ForecastScoreRead,
    KalshiImportCreate,
    KalshiFillImportCreate,
    KalshiFillImportResult,
    KalshiReconciliationRead,
    KalshiRebuildResult,
    KalshiSyncCreate,
    KalshiSyncResult,
    KalshiMarketRead,
    MarketCreate,
    MarketRead,
    MarketUpdate,
    OutcomeCreate,
    OutcomeRead,
    PositionCreate,
    PositionRead,
    PositionUpdate,
    PostmortemCreate,
    PostmortemRead,
    SnapshotCreate,
    SnapshotRead,
)
from .services import (
    add_execution,
    create_bankroll_snapshot,
    create_forecast,
    create_market,
    create_postmortem,
    create_snapshot,
    delete_forecast,
    delete_position,
    create_kalshi_snapshot,
    import_kalshi_market,
    import_kalshi_fills,
    open_position,
    require_market,
    require_position,
    require_forecast,
    resolve_market,
    update_market_from_kalshi,
    update_market,
    update_forecast,
    update_position,
    sync_kalshi_activity,
    rebuild_kalshi_derived_records,
    undo_market_resolution,
)


app = FastAPI(title="Market-Relative Forecast Analytics API")

configured_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
origins = sorted(set(configured_origins + ["http://localhost:3000", "http://127.0.0.1:3000"]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/kalshi/markets/{ticker}", response_model=KalshiMarketRead)
def get_kalshi_market(ticker: str) -> dict[str, object]:
    try:
        return kalshi.search_market(ticker)
    except kalshi.KalshiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/kalshi/import-market", response_model=MarketRead)
def post_kalshi_import(data: KalshiImportCreate, db: Session = Depends(get_db)) -> Market:
    try:
        return import_kalshi_market(db, data.ticker)
    except kalshi.KalshiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/kalshi/import-fills", response_model=KalshiFillImportResult)
def post_kalshi_fill_import(data: KalshiFillImportCreate, db: Session = Depends(get_db)) -> dict[str, int]:
    try:
        return import_kalshi_fills(db, ticker=data.ticker, min_ts=data.min_ts, max_ts=data.max_ts)
    except kalshi.KalshiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/kalshi/sync", response_model=KalshiSyncResult)
def post_kalshi_sync(data: KalshiSyncCreate, db: Session = Depends(get_db)) -> dict[str, int]:
    try:
        return sync_kalshi_activity(
            db,
            ticker=data.ticker,
            min_ts=data.min_ts,
            max_ts=data.max_ts,
            include_historical=data.include_historical,
        )
    except kalshi.KalshiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/kalshi/reconciliation", response_model=KalshiReconciliationRead)
def get_kalshi_reconciliation(db: Session = Depends(get_db)) -> dict[str, object]:
    latest_raw_import_at = max(
        (
            value
            for value in [
                db.scalar(select(func.max(KalshiFill.imported_at))),
                db.scalar(select(func.max(KalshiOrder.imported_at))),
                db.scalar(select(func.max(KalshiSettlement.imported_at))),
                db.scalar(select(func.max(KalshiPositionSnapshot.imported_at))),
                db.scalar(select(func.max(KalshiBalanceSnapshot.imported_at))),
            ]
            if value is not None
        ),
        default=None,
    )
    return {
        "raw_fills": db.scalar(select(func.count(KalshiFill.id))) or 0,
        "unconverted_fills": db.scalar(select(func.count(KalshiFill.id)).where(KalshiFill.imported_execution_id.is_(None))) or 0,
        "raw_orders": db.scalar(select(func.count(KalshiOrder.id))) or 0,
        "raw_settlements": db.scalar(select(func.count(KalshiSettlement.id))) or 0,
        "unconverted_settlements": db.scalar(select(func.count(KalshiSettlement.id)).where(KalshiSettlement.imported_outcome_id.is_(None))) or 0,
        "raw_position_snapshots": db.scalar(select(func.count(KalshiPositionSnapshot.id))) or 0,
        "raw_balance_snapshots": db.scalar(select(func.count(KalshiBalanceSnapshot.id))) or 0,
        "raw_deposits": db.scalar(select(func.count(KalshiDeposit.id))) or 0,
        "raw_withdrawals": db.scalar(select(func.count(KalshiWithdrawal.id))) or 0,
        "imported_positions_missing_forecast": db.scalar(
            select(func.count(Position.id)).where(
                Position.linked_forecast_id.is_(None),
                Position.position_notes.ilike("%Imported from Kalshi%"),
            )
        ) or 0,
        "imported_open_positions": db.scalar(
            select(func.count(Position.id)).where(
                Position.status.in_(["open", "partially_closed"]),
                Position.position_notes.ilike("%Imported from Kalshi%"),
            )
        ) or 0,
        "resolved_markets_needing_review": _pending_postmortem_count(db),
        "latest_raw_import_at": latest_raw_import_at,
        "latest_balance_snapshot_at": db.scalar(select(func.max(KalshiBalanceSnapshot.imported_at))),
    }


@app.post("/kalshi/rebuild-derived", response_model=KalshiRebuildResult)
def post_kalshi_rebuild(db: Session = Depends(get_db)) -> dict[str, int]:
    try:
        return rebuild_kalshi_derived_records(db)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/markets", response_model=list[MarketRead])
def list_markets(db: Session = Depends(get_db)) -> list[Market]:
    return list(db.scalars(select(Market).order_by(Market.expected_resolution_date.asc(), Market.created_at.desc())))


@app.post("/markets", response_model=MarketRead)
def post_market(data: MarketCreate, db: Session = Depends(get_db)) -> Market:
    return create_market(db, data)


@app.get("/markets/{market_id}", response_model=MarketRead)
def get_market(market_id: uuid.UUID, db: Session = Depends(get_db)) -> Market:
    return require_market(db, market_id)


@app.patch("/markets/{market_id}", response_model=MarketRead)
def patch_market(market_id: uuid.UUID, data: MarketUpdate, db: Session = Depends(get_db)) -> Market:
    return update_market(db, market_id, data)


@app.post("/markets/{market_id}/sync-kalshi", response_model=MarketRead)
def post_market_sync_kalshi(market_id: uuid.UUID, db: Session = Depends(get_db)) -> Market:
    try:
        return update_market_from_kalshi(db, market_id)
    except kalshi.KalshiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/markets/{market_id}/snapshots", response_model=list[SnapshotRead])
def list_snapshots(market_id: uuid.UUID, db: Session = Depends(get_db)) -> list[MarketSnapshot]:
    require_market(db, market_id)
    return list(
        db.scalars(
            select(MarketSnapshot)
            .where(MarketSnapshot.market_id == market_id)
            .order_by(MarketSnapshot.timestamp.desc())
        )
    )


@app.post("/markets/{market_id}/snapshots", response_model=SnapshotRead)
def post_snapshot(market_id: uuid.UUID, data: SnapshotCreate, db: Session = Depends(get_db)) -> MarketSnapshot:
    return create_snapshot(db, market_id, data)


@app.post("/markets/{market_id}/snapshots/kalshi", response_model=SnapshotRead)
def post_kalshi_snapshot(market_id: uuid.UUID, db: Session = Depends(get_db)) -> MarketSnapshot:
    try:
        return create_kalshi_snapshot(db, market_id)
    except kalshi.KalshiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/markets/{market_id}/forecasts", response_model=list[ForecastRead])
def list_forecasts(market_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Forecast]:
    require_market(db, market_id)
    return list(db.scalars(select(Forecast).where(Forecast.market_id == market_id).order_by(Forecast.timestamp.desc())))


@app.post("/markets/{market_id}/forecasts", response_model=ForecastRead)
def post_forecast(market_id: uuid.UUID, data: ForecastCreate, db: Session = Depends(get_db)) -> Forecast:
    return create_forecast(db, market_id, data)


@app.get("/forecasts/{forecast_id}", response_model=ForecastRead)
def get_forecast(forecast_id: uuid.UUID, db: Session = Depends(get_db)) -> Forecast:
    return require_forecast(db, forecast_id)


@app.patch("/forecasts/{forecast_id}", response_model=ForecastRead)
def patch_forecast(forecast_id: uuid.UUID, data: ForecastUpdate, db: Session = Depends(get_db)) -> Forecast:
    return update_forecast(db, forecast_id, data)


@app.delete("/forecasts/{forecast_id}")
def remove_forecast(forecast_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, bool]:
    delete_forecast(db, forecast_id)
    return {"deleted": True}


@app.get("/markets/{market_id}/positions", response_model=list[PositionRead])
def list_market_positions(market_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Position]:
    require_market(db, market_id)
    return list(db.scalars(select(Position).where(Position.market_id == market_id).order_by(Position.opened_at.desc())))


@app.post("/markets/{market_id}/resolve", response_model=OutcomeRead)
def post_resolution(market_id: uuid.UUID, data: OutcomeCreate, db: Session = Depends(get_db)) -> Outcome:
    return resolve_market(db, market_id, data)


@app.delete("/markets/{market_id}/resolution", response_model=MarketRead)
def delete_resolution(market_id: uuid.UUID, db: Session = Depends(get_db)) -> Market:
    return undo_market_resolution(db, market_id)


@app.get("/markets/{market_id}/scores", response_model=list[ForecastScoreRead])
def list_scores(market_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ForecastScore]:
    require_market(db, market_id)
    return list(db.scalars(select(ForecastScore).where(ForecastScore.market_id == market_id)))


@app.get("/positions", response_model=list[PositionRead])
def list_positions(db: Session = Depends(get_db)) -> list[Position]:
    return list(db.scalars(select(Position).order_by(Position.opened_at.desc())))


@app.post("/positions", response_model=PositionRead)
def post_position(data: PositionCreate, db: Session = Depends(get_db)) -> Position:
    return open_position(db, data)


@app.get("/positions/{position_id}", response_model=PositionRead)
def get_position(position_id: uuid.UUID, db: Session = Depends(get_db)) -> Position:
    return require_position(db, position_id)


@app.patch("/positions/{position_id}", response_model=PositionRead)
def patch_position(position_id: uuid.UUID, data: PositionUpdate, db: Session = Depends(get_db)) -> Position:
    return update_position(db, position_id, data)


@app.delete("/positions/{position_id}")
def remove_position(position_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, bool]:
    delete_position(db, position_id)
    return {"deleted": True}


@app.get("/positions/{position_id}/executions", response_model=list[ExecutionRead])
def list_executions(position_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Execution]:
    require_position(db, position_id)
    return list(db.scalars(select(Execution).where(Execution.position_id == position_id).order_by(Execution.timestamp.asc())))


@app.post("/positions/{position_id}/executions", response_model=ExecutionRead)
def post_execution(position_id: uuid.UUID, data: ExecutionCreate, db: Session = Depends(get_db)) -> Execution:
    return add_execution(db, position_id, data)


@app.get("/bankroll-snapshots", response_model=list[BankrollSnapshotRead])
def list_bankroll_snapshots(db: Session = Depends(get_db)) -> list[BankrollSnapshot]:
    return list(db.scalars(select(BankrollSnapshot).order_by(BankrollSnapshot.timestamp.desc())))


@app.post("/bankroll-snapshots", response_model=BankrollSnapshotRead)
def post_bankroll_snapshot(data: BankrollSnapshotCreate, db: Session = Depends(get_db)) -> BankrollSnapshot:
    return create_bankroll_snapshot(db, data)


@app.get("/postmortems", response_model=list[PostmortemRead])
def list_postmortems(db: Session = Depends(get_db)) -> list[Postmortem]:
    return list(db.scalars(select(Postmortem).order_by(Postmortem.reviewed_at.desc())))


@app.post("/postmortems", response_model=PostmortemRead)
def post_postmortem(data: PostmortemCreate, db: Session = Depends(get_db)) -> Postmortem:
    return create_postmortem(db, data)


@app.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    forecast_count = db.scalar(select(func.count(Forecast.id))) or 0
    score_count = db.scalar(select(func.count(ForecastScore.id))) or 0
    position_count = db.scalar(select(func.count(Position.id))) or 0
    open_positions = db.scalar(select(func.count(Position.id)).where(Position.status.in_(["open", "partially_closed"]))) or 0
    total_realized = db.scalar(select(func.coalesce(func.sum(Position.realized_pnl_minor_units), 0))) or 0
    total_pnl = db.scalar(select(func.coalesce(func.sum(Position.total_pnl_minor_units), 0))) or 0
    open_exposure = db.scalar(
        select(func.coalesce(func.sum(Position.remaining_cost_basis_minor_units), 0)).where(
            Position.status.in_(["open", "partially_closed"])
        )
    ) or 0
    latest_bankroll = db.scalar(select(BankrollSnapshot).order_by(BankrollSnapshot.timestamp.desc()).limit(1))
    latest_kalshi_balance = db.scalar(select(KalshiBalanceSnapshot).order_by(KalshiBalanceSnapshot.imported_at.desc()).limit(1))
    latest_raw_import_at = max(
        (
            value
            for value in [
                db.scalar(select(func.max(KalshiFill.imported_at))),
                db.scalar(select(func.max(KalshiOrder.imported_at))),
                db.scalar(select(func.max(KalshiSettlement.imported_at))),
                db.scalar(select(func.max(KalshiPositionSnapshot.imported_at))),
                db.scalar(select(func.max(KalshiBalanceSnapshot.imported_at))),
            ]
            if value is not None
        ),
        default=None,
    )
    avg_brier = db.scalar(select(func.avg(ForecastScore.brier_user_bps_squared)))
    avg_market_brier = db.scalar(select(func.avg(ForecastScore.brier_market_bps_squared)))
    avg_improvement = db.scalar(select(func.avg(ForecastScore.brier_improvement_bps_squared)))
    return {
        "forecasting": {
            "forecasts": forecast_count,
            "resolved_forecasts": score_count,
            "average_brier": _score_display(avg_brier),
            "average_market_brier": _score_display(avg_market_brier),
            "average_brier_improvement": _score_display(avg_improvement),
        },
        "trading": {
            "positions": position_count,
            "open_positions": open_positions,
            "realized_pnl_minor_units": total_realized,
            "total_pnl_minor_units": total_pnl,
        },
        "exposure": {
            "open_exposure_minor_units": open_exposure,
            "latest_total_equity_minor_units": latest_bankroll.total_equity_minor_units if latest_bankroll else None,
            "latest_kalshi_balance_minor_units": latest_kalshi_balance.balance_minor_units if latest_kalshi_balance else None,
            "latest_kalshi_portfolio_value_minor_units": latest_kalshi_balance.portfolio_value_minor_units if latest_kalshi_balance else None,
        },
        "data_health": {
            "latest_raw_import_at": latest_raw_import_at,
            "unconverted_fills": db.scalar(select(func.count(KalshiFill.id)).where(KalshiFill.imported_execution_id.is_(None))) or 0,
            "unconverted_settlements": db.scalar(select(func.count(KalshiSettlement.id)).where(KalshiSettlement.imported_outcome_id.is_(None))) or 0,
            "positions_missing_forecast": db.scalar(
                select(func.count(Position.id)).where(
                    Position.linked_forecast_id.is_(None),
                    Position.position_notes.ilike("%Imported from Kalshi%"),
                )
            ) or 0,
            "resolved_markets_needing_review": _pending_postmortem_count(db),
        },
    }


def _score_display(value: object) -> float | None:
    if value is None:
        return None
    return round(float(value) / 100_000_000, 6)


def _pending_postmortem_count(db: Session) -> int:
    reviewed_position_ids = {
        row[0]
        for row in db.execute(select(Postmortem.position_id).where(Postmortem.position_id.is_not(None)))
        if row[0] is not None
    }
    position_query = select(func.count(Position.id)).where(Position.status.in_(["closed_before_resolution", "resolved", "voided"]))
    if reviewed_position_ids:
        position_query = position_query.where(Position.id.not_in(reviewed_position_ids))
    pending_positions = db.scalar(position_query) or 0

    market_ids_with_positions = {row[0] for row in db.execute(select(Position.market_id))}
    reviewed_market_ids = {
        row[0]
        for row in db.execute(select(Postmortem.market_id).where(Postmortem.position_id.is_(None)))
        if row[0] is not None
    }
    market_query = select(func.count(Market.id)).where(Market.status.in_(["resolved", "voided", "ambiguous"]))
    if market_ids_with_positions:
        market_query = market_query.where(Market.id.not_in(market_ids_with_positions))
    if reviewed_market_ids:
        market_query = market_query.where(Market.id.not_in(reviewed_market_ids))
    pending_markets = db.scalar(market_query) or 0
    return int(pending_positions) + int(pending_markets)


@app.get("/exports/{name}.csv")
def export_csv(name: str, db: Session = Depends(get_db)) -> Response:
    tables = {
        "markets": Market,
        "forecasts": Forecast,
        "positions": Position,
        "executions": Execution,
        "outcomes": Outcome,
        "postmortems": Postmortem,
        "bankroll-snapshots": BankrollSnapshot,
        "kalshi-fills": KalshiFill,
        "kalshi-orders": KalshiOrder,
        "kalshi-settlements": KalshiSettlement,
        "kalshi-position-snapshots": KalshiPositionSnapshot,
        "kalshi-balance-snapshots": KalshiBalanceSnapshot,
        "kalshi-deposits": KalshiDeposit,
        "kalshi-withdrawals": KalshiWithdrawal,
    }
    model = tables.get(name)
    if model is None:
        return Response("unknown export", status_code=404)
    rows = list(db.scalars(select(model)))
    output = io.StringIO()
    writer = csv.writer(output)
    columns = [column.name for column in model.__table__.columns]
    writer.writerow(columns)
    for row in rows:
        writer.writerow([getattr(row, column) for column in columns])
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}.csv"'},
    )
