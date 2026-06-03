from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import make_url

from .database import DATABASE_URL, engine


def main() -> None:
    url = make_url(DATABASE_URL)
    safe_url = url.set(password="***" if url.password else None)
    print(f"Driver: {url.drivername}")
    print(f"Host: {url.host}")
    print(f"Port: {url.port}")
    print(f"Database: {url.database}")
    print(f"URL: {safe_url}")
    with engine.connect() as connection:
        value = connection.execute(text("select 1")).scalar_one()
    print(f"Connection OK: {value}")


if __name__ == "__main__":
    main()
