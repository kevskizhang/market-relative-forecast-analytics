from __future__ import annotations

import sys

from .kalshi import search_market


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.check_kalshi <ticker-or-url>")
    market = search_market(sys.argv[1])
    print(f"Ticker: {market['ticker']}")
    print(f"Title: {market['title']}")
    print(f"Market URL: {market['market_url']}")
    print(f"Market YES bps: {market['market_probability_yes_bps']}")
    print(f"YES bid bps: {market['yes_bid_bps']}")
    print(f"YES ask bps: {market['yes_ask_bps']}")


if __name__ == "__main__":
    main()
