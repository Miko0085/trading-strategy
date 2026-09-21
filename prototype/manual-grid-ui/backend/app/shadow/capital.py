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


def side_budgets(snapshot: CapitalSnapshot, long_pct: Decimal, short_pct: Decimal, reserve_pct: Decimal, *, opposite_upnl_reinvestment_pct: Decimal = Decimal("0"), opposite_unrealized_pnl: Decimal = Decimal("0")) -> dict[str, Decimal]:
    if snapshot.capital_base is None or long_pct + short_pct + reserve_pct != 100:
        raise ValueError("capital base and allocation percentages are required")
    experimental = max(Decimal("0"), opposite_unrealized_pnl) * opposite_upnl_reinvestment_pct / 100
    return {"long": snapshot.capital_base * long_pct / 100 + experimental, "short": snapshot.capital_base * short_pct / 100 + experimental, "reserve": snapshot.capital_base * reserve_pct / 100}
