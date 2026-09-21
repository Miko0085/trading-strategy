from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal


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
) -> dict[str, Decimal]:
    """Return the one canonical capital allocation policy.

    Percentages are percentages, not fractions.  Allocation may intentionally
    leave capital unallocated (Long + Short + Reserve <= 100).  Reinvestment
    is side-specific and is capped by the non-reserve capital guard.
    """
    total_pct = long_pct + short_pct + reserve_pct
    if snapshot.capital_base is None or total_pct > 100 or min(long_pct, short_pct, reserve_pct) < 0:
        raise ValueError("capital base and allocation percentages are required")
    base_long = snapshot.capital_base * long_pct / 100
    base_short = snapshot.capital_base * short_pct / 100
    reserve = snapshot.capital_base * reserve_pct / 100
    requested_long_extra = max(Decimal("0"), short_unrealized_pnl) * max(Decimal("0"), short_to_long_reinvestment_pct) / 100
    requested_short_extra = max(Decimal("0"), long_unrealized_pnl) * max(Decimal("0"), long_to_short_reinvestment_pct) / 100
    extra_room = max(Decimal("0"), snapshot.capital_base - reserve - base_long - base_short)
    requested_extra = requested_long_extra + requested_short_extra
    scale = min(Decimal("1"), extra_room / requested_extra) if requested_extra else Decimal("1")
    result = {
        "long": base_long + requested_long_extra * scale,
        "short": base_short + requested_short_extra * scale,
        "reserve": reserve,
    }
    if requested_long_extra or requested_short_extra:
        result["long_extra"] = requested_long_extra * scale
        result["short_extra"] = requested_short_extra * scale
    return result
