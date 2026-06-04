from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import urllib.error
import base64
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


KALSHI_API_BASE_URL = os.getenv("KALSHI_API_BASE_URL", "https://external-api.kalshi.com/trade-api/v2").rstrip("/")
KALSHI_WEB_BASE_URL = os.getenv("KALSHI_WEB_BASE_URL", "https://kalshi.com")
KALSHI_ACCESS_KEY = os.getenv("KALSHI_ACCESS_KEY")
KALSHI_PRIVATE_KEY_PATH = os.getenv("KALSHI_PRIVATE_KEY_PATH")
KALSHI_PRIVATE_KEY_PEM = os.getenv("KALSHI_PRIVATE_KEY_PEM")


class KalshiError(RuntimeError):
    pass


def get_market(ticker: str) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    payload = _get_json(f"/markets/{urllib.parse.quote(ticker)}")
    market = payload.get("market", payload)
    if not isinstance(market, dict):
        raise KalshiError("Kalshi market response did not include a market object")
    return normalize_market(market)


def search_market(ticker: str) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    query = urllib.parse.urlencode({"tickers": ticker, "limit": 1})
    payload = _get_json(f"/markets?{query}")
    markets = payload.get("markets", [])
    if not markets:
        return get_market(ticker)
    return normalize_market(markets[0])


def get_fills(ticker: str | None = None, min_ts: int | None = None, max_ts: int | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    query: dict[str, object] = {"limit": min(max(limit, 1), 1000)}
    if ticker:
        query["ticker"] = normalize_ticker(ticker)
    if min_ts is not None:
        query["min_ts"] = min_ts
    if max_ts is not None:
        query["max_ts"] = max_ts
    return _paginate_authenticated("/portfolio/fills", query, "fills")


def get_historical_fills(ticker: str | None = None, min_ts: int | None = None, max_ts: int | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    query: dict[str, object] = {"limit": min(max(limit, 1), 1000)}
    if ticker:
        query["ticker"] = normalize_ticker(ticker)
    if min_ts is not None:
        query["min_ts"] = min_ts
    if max_ts is not None:
        query["max_ts"] = max_ts
    return _paginate_authenticated("/historical/fills", query, "fills")


def get_orders(ticker: str | None = None, min_ts: int | None = None, max_ts: int | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    query: dict[str, object] = {"limit": min(max(limit, 1), 1000)}
    if ticker:
        query["ticker"] = normalize_ticker(ticker)
    if min_ts is not None:
        query["min_ts"] = min_ts
    if max_ts is not None:
        query["max_ts"] = max_ts
    return _paginate_authenticated("/portfolio/orders", query, "orders")


def get_settlements(ticker: str | None = None, min_ts: int | None = None, max_ts: int | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    query: dict[str, object] = {"limit": min(max(limit, 1), 1000)}
    if ticker:
        query["ticker"] = normalize_ticker(ticker)
    if min_ts is not None:
        query["min_ts"] = min_ts
    if max_ts is not None:
        query["max_ts"] = max_ts
    return _paginate_authenticated("/portfolio/settlements", query, "settlements")


def get_positions(limit: int = 1000) -> list[dict[str, Any]]:
    query: dict[str, object] = {"limit": min(max(limit, 1), 1000)}
    return _paginate_authenticated("/portfolio/positions", query, ("market_positions", "positions"))


def get_balance() -> dict[str, Any]:
    return _authenticated_get_json("/portfolio/balance")


def get_deposits(limit: int = 500) -> list[dict[str, Any]]:
    query: dict[str, object] = {"limit": min(max(limit, 1), 500)}
    return _paginate_authenticated("/portfolio/deposits", query, "deposits")


def get_withdrawals(limit: int = 500) -> list[dict[str, Any]]:
    query: dict[str, object] = {"limit": min(max(limit, 1), 500)}
    return _paginate_authenticated("/portfolio/withdrawals", query, "withdrawals")


def normalize_ticker(value: str) -> str:
    value = value.strip()
    if not value:
        raise KalshiError("Kalshi ticker is required")
    if "kalshi.com" in value:
        parsed = urllib.parse.urlparse(value)
        path_parts = [part for part in parsed.path.split("/") if part]
        if not path_parts:
            raise KalshiError("Kalshi URL did not include a market ticker")
        value = path_parts[-1]
    value = value.split("?", 1)[0].split("#", 1)[0].strip().strip("/")
    return value.upper()


def normalize_market(market: dict[str, Any]) -> dict[str, Any]:
    ticker = str(market.get("ticker") or market.get("market_ticker") or "").upper()
    if not ticker:
        raise KalshiError("Kalshi market is missing ticker")

    yes_bid_bps = _price_to_bps(market.get("yes_bid_dollars"), market.get("yes_bid"))
    yes_ask_bps = _price_to_bps(market.get("yes_ask_dollars"), market.get("yes_ask"))
    last_price_bps = _price_to_bps(market.get("last_price_dollars"), market.get("last_price"))
    market_probability_yes_bps = _first_int(
        yes_bid_bps,
        last_price_bps,
        _price_to_bps(market.get("yes_price_dollars"), market.get("yes_price")),
        yes_ask_bps,
    )

    close_value = market.get("close_time") or market.get("expected_expiration_time") or market.get("expiration_time")
    expected_resolution_date = _date_from_value(close_value)

    return {
        "ticker": ticker,
        "event_ticker": market.get("event_ticker"),
        "title": market.get("title") or market.get("subtitle") or ticker,
        "description": market.get("rules_primary") or market.get("description") or market.get("subtitle"),
        "category": market.get("category") or "Kalshi",
        "market_url": _market_url(ticker),
        "resolution_criteria": market.get("rules_primary") or market.get("rules_secondary") or market.get("title") or ticker,
        "expected_resolution_date": expected_resolution_date.isoformat() if expected_resolution_date else None,
        "status": market.get("status"),
        "yes_bid_bps": yes_bid_bps,
        "yes_ask_bps": yes_ask_bps,
        "last_trade_price_bps": last_price_bps,
        "market_probability_yes_bps": market_probability_yes_bps,
        "volume": _int_or_none(market.get("volume")),
        "open_interest": _int_or_none(market.get("open_interest")),
        "raw": market,
    }


def _get_json(path: str) -> dict[str, Any]:
    url = f"{KALSHI_API_BASE_URL}{path}"
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "mrf-analytics/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise KalshiError(
                f"Kalshi did not find that market at {url}. Use the specific market ticker from Kalshi, not an event page slug."
            ) from exc
        raise KalshiError(f"Kalshi request failed for {url}: HTTP {exc.code}") from exc
    except Exception as exc:  # pragma: no cover - network failure branch
        raise KalshiError(f"Kalshi request failed for {url}: {exc}") from exc


def _paginate_authenticated(path: str, query: dict[str, object], item_key: str | tuple[str, ...]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        current_query = dict(query)
        if cursor:
            current_query["cursor"] = cursor
        query_string = urllib.parse.urlencode(current_query)
        payload = _authenticated_get_json(f"{path}?{query_string}" if query_string else path)
        keys = (item_key,) if isinstance(item_key, str) else item_key
        page_items = []
        for key in keys:
            if key in payload:
                page_items = payload.get(key, [])
                break
        if not isinstance(page_items, list):
            raise KalshiError(f"Kalshi response did not include one of {keys} as a list")
        items.extend(page_items)
        cursor = payload.get("cursor")
        if not cursor:
            return items


def _authenticated_get_json(path: str) -> dict[str, Any]:
    if not KALSHI_ACCESS_KEY:
        raise KalshiError("KALSHI_ACCESS_KEY is not configured")
    url = f"{KALSHI_API_BASE_URL}{path}"
    method = "GET"
    timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000))
    sign_path = urllib.parse.urlparse(url).path
    signature = _sign(timestamp + method + sign_path)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "mrf-analytics/0.1",
            "KALSHI-ACCESS-KEY": KALSHI_ACCESS_KEY,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "KALSHI-ACCESS-SIGNATURE": signature,
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise KalshiError(f"Kalshi authenticated request failed for {url}: HTTP {exc.code} {body}") from exc
    except Exception as exc:  # pragma: no cover
        raise KalshiError(f"Kalshi authenticated request failed for {url}: {exc}") from exc


def _sign(text: str) -> str:
    private_key = _load_private_key()
    signature = private_key.sign(
        text.encode("utf-8"),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def _load_private_key() -> rsa.RSAPrivateKey:
    if KALSHI_PRIVATE_KEY_PEM:
        raw = KALSHI_PRIVATE_KEY_PEM.encode("utf-8")
    elif KALSHI_PRIVATE_KEY_PATH:
        raw = Path(KALSHI_PRIVATE_KEY_PATH).read_bytes()
    else:
        raise KalshiError("KALSHI_PRIVATE_KEY_PATH or KALSHI_PRIVATE_KEY_PEM is not configured")
    key = serialization.load_pem_private_key(raw, password=None, backend=default_backend())
    if not isinstance(key, rsa.RSAPrivateKey):
        raise KalshiError("Kalshi private key must be an RSA private key")
    return key


def _price_to_bps(dollars_value: Any, cents_value: Any = None) -> int | None:
    if dollars_value is not None:
        return _decimal_to_bps(dollars_value)
    if cents_value is not None:
        try:
            return int(Decimal(str(cents_value)) * Decimal("100"))
        except (InvalidOperation, ValueError):
            return None
    return None


def _decimal_to_bps(value: Any) -> int | None:
    try:
        return int((Decimal(str(value)) * Decimal("10000")).to_integral_value())
    except (InvalidOperation, ValueError):
        return None


def _first_int(*values: int | None) -> int | None:
    for value in values:
        if value is not None:
            return value
    return None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _date_from_value(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def _market_url(ticker: str) -> str:
    return f"{KALSHI_WEB_BASE_URL.rstrip('/')}/markets/{ticker.lower()}"
