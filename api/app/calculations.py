from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

BPS_DENOMINATOR = 10_000
CENTS_PER_CONTRACT = 100


def clamp_bps(value: int) -> int:
    if value < 0 or value > BPS_DENOMINATOR:
        raise ValueError("basis-point value must be between 0 and 10000")
    return value


def edge_bps(forecast_probability_yes_bps: int, market_probability_yes_bps: int) -> int:
    clamp_bps(forecast_probability_yes_bps)
    clamp_bps(market_probability_yes_bps)
    return forecast_probability_yes_bps - market_probability_yes_bps


def expected_value_bps(side: str, forecast_probability_yes_bps: int, entry_price_bps: int) -> int:
    clamp_bps(forecast_probability_yes_bps)
    clamp_bps(entry_price_bps)
    if side == "YES":
        return forecast_probability_yes_bps - entry_price_bps
    if side == "NO":
        return (BPS_DENOMINATOR - forecast_probability_yes_bps) - entry_price_bps
    raise ValueError("side must be YES or NO")


def brier_scores_bps_squared(
    forecast_probability_yes_bps: int,
    market_probability_yes_bps: int,
    final_outcome: str,
) -> tuple[int, int, int, int]:
    if final_outcome == "YES":
        outcome_value_bps = BPS_DENOMINATOR
    elif final_outcome == "NO":
        outcome_value_bps = 0
    else:
        raise ValueError("Brier score is only defined for YES or NO outcomes")

    user_score = (forecast_probability_yes_bps - outcome_value_bps) ** 2
    market_score = (market_probability_yes_bps - outcome_value_bps) ** 2
    return outcome_value_bps, user_score, market_score, market_score - user_score


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _round_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def contract_value_minor_units(quantity: object, price_bps: int) -> int:
    qty = _decimal(quantity)
    if qty < 0:
        raise ValueError("quantity must be non-negative")
    clamp_bps(price_bps)
    value = qty * Decimal(price_bps) * Decimal(CENTS_PER_CONTRACT) / Decimal(BPS_DENOMINATOR)
    return _round_cents(value)


def buy_cost_minor_units(quantity: object, price_bps: int, fees_minor_units: int = 0) -> int:
    if fees_minor_units < 0:
        raise ValueError("fees must be non-negative")
    return contract_value_minor_units(quantity, price_bps) + fees_minor_units


def sell_proceeds_minor_units(quantity: object, price_bps: int, fees_minor_units: int = 0) -> int:
    if fees_minor_units < 0:
        raise ValueError("fees must be non-negative")
    return contract_value_minor_units(quantity, price_bps) - fees_minor_units


def average_price_bps(total_minor_units: int, quantity: object) -> int | None:
    qty = _decimal(quantity)
    if qty <= 0:
        return None
    value = Decimal(total_minor_units) * Decimal(BPS_DENOMINATOR) / (qty * Decimal(CENTS_PER_CONTRACT))
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
