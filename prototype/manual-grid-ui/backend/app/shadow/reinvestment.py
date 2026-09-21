from __future__ import annotations

from decimal import Decimal


ZERO = Decimal("0")


def realized_reinvest_amount(net_realized_profit: Decimal | None, reinvest_pct: Decimal) -> Decimal:
    """Persistent compounding from a confirmed positive net realized result."""
    if net_realized_profit is None or net_realized_profit <= ZERO or reinvest_pct <= ZERO:
        return ZERO
    return net_realized_profit * reinvest_pct / Decimal("100")


def next_strategy_deposit(previous_deposit: Decimal, net_realized_profit: Decimal | None, reinvest_pct: Decimal) -> Decimal:
    return previous_deposit + realized_reinvest_amount(net_realized_profit, reinvest_pct)


def calculate_effective_side_budget(
    *, capital_base: Decimal, long_pct: Decimal, short_pct: Decimal, reserve_pct: Decimal,
    previous_long_deposit: Decimal | None = None, previous_short_deposit: Decimal | None = None,
    long_net_realized_profit: Decimal | None = None, short_net_realized_profit: Decimal | None = None,
    long_realized_reinvest_pct: Decimal = ZERO, short_realized_reinvest_pct: Decimal = ZERO,
    long_unrealized_pnl: Decimal | None = None, short_unrealized_pnl: Decimal | None = None,
    long_unrealized_reinvest_pct: Decimal = ZERO, short_unrealized_reinvest_pct: Decimal = ZERO,
) -> dict[str, Decimal]:
    """Return persistent deposits and temporary boosts with reserve protection.

    Deposit growth is applied first.  Floating PnL is only a temporary boost;
    both are capped so effective side budgets never consume the reserve.
    """
    reserve = capital_base * reserve_pct / 100
    base_long = capital_base * long_pct / 100
    base_short = capital_base * short_pct / 100
    long_reinvest = realized_reinvest_amount(long_net_realized_profit, long_realized_reinvest_pct)
    short_reinvest = realized_reinvest_amount(short_net_realized_profit, short_realized_reinvest_pct)
    long_deposit = next_strategy_deposit(previous_long_deposit if previous_long_deposit is not None else base_long, long_net_realized_profit, long_realized_reinvest_pct)
    short_deposit = next_strategy_deposit(previous_short_deposit if previous_short_deposit is not None else base_short, short_net_realized_profit, short_realized_reinvest_pct)
    non_reserve = max(ZERO, capital_base - reserve)
    deposit_total = long_deposit + short_deposit
    deposit_scale = min(Decimal("1"), non_reserve / deposit_total) if deposit_total else Decimal("1")
    long_deposit *= deposit_scale
    short_deposit *= deposit_scale
    long_requested = max(ZERO, short_unrealized_pnl or ZERO) * max(ZERO, long_unrealized_reinvest_pct) / 100
    short_requested = max(ZERO, long_unrealized_pnl or ZERO) * max(ZERO, short_unrealized_reinvest_pct) / 100
    boost_capacity = max(ZERO, non_reserve - long_deposit - short_deposit)
    requested_total = long_requested + short_requested
    boost_scale = min(Decimal("1"), boost_capacity / requested_total) if requested_total else Decimal("1")
    long_boost = long_requested * boost_scale
    short_boost = short_requested * boost_scale
    return {
        "base_long_budget": base_long, "base_short_budget": base_short,
        "long_strategy_deposit": long_deposit, "short_strategy_deposit": short_deposit,
        "long_realized_reinvest": long_reinvest, "short_realized_reinvest": short_reinvest,
        "long_unrealized_requested": long_requested, "short_unrealized_requested": short_requested,
        "long_unrealized_boost": long_boost, "short_unrealized_boost": short_boost,
        "long": long_deposit + long_boost, "short": short_deposit + short_boost,
        "reserve": reserve, "capital_base": capital_base,
    }
