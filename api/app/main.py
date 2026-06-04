from __future__ import annotations

import csv
import io
import os
import uuid

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
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
)
from .schemas import (
    BankrollSnapshotCreate,
    BankrollSnapshotRead,
    ExecutionCreate,
    ExecutionRead,
    ForecastCreate,
    ForecastRead,
    ForecastScoreRead,
    MarketCreate,
    MarketRead,
    MarketUpdate,
    OutcomeCreate,
    OutcomeRead,
    PositionCreate,
    PositionRead,
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
    open_position,
    require_market,
    require_position,
    resolve_market,
    update_market,
)


app = FastAPI(title="Market-Relative Forecast Analytics API")

origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
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


@app.get("/markets/{market_id}/forecasts", response_model=list[ForecastRead])
def list_forecasts(market_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Forecast]:
    require_market(db, market_id)
    return list(db.scalars(select(Forecast).where(Forecast.market_id == market_id).order_by(Forecast.timestamp.desc())))


@app.post("/markets/{market_id}/forecasts", response_model=ForecastRead)
def post_forecast(market_id: uuid.UUID, data: ForecastCreate, db: Session = Depends(get_db)) -> Forecast:
    return create_forecast(db, market_id, data)


@app.get("/markets/{market_id}/positions", response_model=list[PositionRead])
def list_market_positions(market_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Position]:
    require_market(db, market_id)
    return list(db.scalars(select(Position).where(Position.market_id == market_id).order_by(Position.opened_at.desc())))


@app.post("/markets/{market_id}/resolve", response_model=OutcomeRead)
def post_resolution(market_id: uuid.UUID, data: OutcomeCreate, db: Session = Depends(get_db)) -> Outcome:
    return resolve_market(db, market_id, data)


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
        },
    }


def _score_display(value: object) -> float | None:
    if value is None:
        return None
    return round(float(value) / 100_000_000, 6)


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
