from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from .database import DATABASE_URL, Base, engine
from . import models  # noqa: F401


def main() -> None:
    url = make_url(DATABASE_URL)
    safe_url = url.set(password="***" if url.password else None)
    print(f"Initializing database: {safe_url}")
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    print("Tables:")
    for table in tables:
        print(f"- {table}")


if __name__ == "__main__":
    main()
