from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal

from .reinvestment import calculate_effective_side_budget


@dataclass(frozen=True)
class CapitalSnapshot:
    wallet_balance: Decimal | None
    equity: Decimal | None
    available_margin: Decimal | None
    realized_pnl: Decimal | None
    unrealized_pnl: Decimal | None
    capital_base: Decimal | None
    formula: str

    def as_dict(self) -> dict[str, object]:
        return {key: str(value) if isinstance(value, Decimal) else value for key, value in asdict(self).items()}


def capital_snapshot(account: dict[str, object], *, capital_base_field: str = "available_margin") -> CapitalSnapshot:
    def decimal(key: str) -> Decimal | None:
        value = account.get(key)
        return None if value in (None, "") else Decimal(str(value))

    available = decimal("available_margin")
    base = decimal(capital_base_field)
    return CapitalSnapshot(decimal("wallet_balance"), decimal("equity"), available, decimal("realized_pnl"), decimal("unrealized_pnl"), base, f"capital_base = factual account.{capital_base_field}; replaceable policy")


def side_budgets(
    snapshot: CapitalSnapshot,
    long_pct: Decimal,
    short_pct: Decimal,
    reserve_pct: Decimal,
    *,
    long_to_short_reinvestment_pct: Decimal = Decimal("0"),
    short_to_long_reinvestment_pct: Decimal = Decimal("0"),
    long_unrealized_pnl: Decimal = Decimal("0"),
    short_unrealized_pnl: Decimal = Decimal("0"),
    long_realized_reinvest_pct: Decimal = Decimal("0"),
    short_realized_reinvest_pct: Decimal = Decimal("0"),
    previous_long_strategy_deposit: Decimal | None = None,
    previous_short_strategy_deposit: Decimal | None = None,
) -> dict[str, Decimal]:
    """Return the one canonical capital allocation policy.

    Percentages are percentages, not fractions.  Allocation may intentionally
    leave capital unallocated (Long + Short + Reserve <= 100).  Reinvestment
    is side-specific and is capped by the non-reserve capital guard.
    """
    total_pct = long_pct + short_pct + reserve_pct
    if snapshot.capital_base is None or total_pct > 100 or min(long_pct, short_pct, reserve_pct) < 0:
        raise ValueError("capital base and allocation percentages are required")
    effective = calculate_effective_side_budget(
        capital_base=snapshot.capital_base, long_pct=long_pct, short_pct=short_pct, reserve_pct=reserve_pct,
        previous_long_deposit=previous_long_strategy_deposit, previous_short_deposit=previous_short_strategy_deposit,
        long_realized_reinvest_pct=long_realized_reinvest_pct, short_realized_reinvest_pct=short_realized_reinvest_pct,
        long_unrealized_pnl=long_unrealized_pnl, short_unrealized_pnl=short_unrealized_pnl,
        long_unrealized_reinvest_pct=short_to_long_reinvestment_pct, short_unrealized_reinvest_pct=long_to_short_reinvestment_pct,
    )
    result = {
        "long": effective["long"], "short": effective["short"], "reserve": effective["reserve"],
    }
    if effective["long_unrealized_requested"] or effective["short_unrealized_requested"]:
        result["long_extra"] = effective["long_unrealized_boost"]
        result["short_extra"] = effective["short_unrealized_boost"]
    return result
