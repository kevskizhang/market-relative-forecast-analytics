from __future__ import annotations

from sqlalchemy import text

from .database import engine


def main() -> None:
    statements = [
        "alter table if exists positions alter column quantity type numeric(18, 6) using quantity::numeric",
        "alter table if exists positions alter column quantity set default 0",
        "alter table if exists executions alter column quantity type numeric(18, 6) using quantity::numeric",
    ]
    with engine.begin() as connection:
        for statement in statements:
            print(statement)
            connection.execute(text(statement))
    print("Decimal quantity migration complete.")


if __name__ == "__main__":
    main()
