from __future__ import annotations

from sqlalchemy import inspect, text

from . import models  # noqa: F401
from .database import Base, engine


def main() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
        execution_columns = {column["name"] for column in inspector.get_columns("executions")} if "executions" in table_names else set()
        if "executions" in table_names and "kalshi_fill_id" not in execution_columns:
            print("Adding executions.kalshi_fill_id")
            connection.execute(text("alter table executions add column kalshi_fill_id text"))
            connection.execute(text("create unique index if not exists ix_executions_kalshi_fill_id on executions(kalshi_fill_id)"))
        print("Creating Kalshi raw sync tables if missing")
        Base.metadata.create_all(bind=connection)
    print("Kalshi fill migration complete.")


if __name__ == "__main__":
    main()
