from decimal import Decimal

import pytest

from app.calculations import allocation_guard, allocation_limits, entry_prices, gross_pnl, tp_price, tp_quantity, weighted_average


def test_entry_chain_long_and_short():
    assert entry_prices(Decimal("100"), "long", [Decimal("10"), Decimal("10")], Decimal("0.1")) == [Decimal("90.0"), Decimal("81.0")]
    assert entry_prices(Decimal("100"), "short", [Decimal("10"), Decimal("10")], Decimal("0.1")) == [Decimal("110.0"), Decimal("121.0")]


def test_weighted_average_and_tp_from_filled_quantity():
    assert weighted_average([(Decimal("3"), Decimal("100")), (Decimal("2"), Decimal("110"))]) == Decimal("104")
    assert tp_quantity(Decimal("3"), Decimal("50")) == Decimal("1.5")
    assert tp_price(Decimal("100"), "long", Decimal("5"), Decimal("0.1")) == Decimal("105.0")
    assert gross_pnl(Decimal("100"), Decimal("105"), Decimal("1.5"), "long") == Decimal("7.5")


def test_allocation_guard_uses_live_available_margin_and_full_grid():
    limits = allocation_limits(Decimal("1000"), Decimal("40"), Decimal("20"), Decimal("40"))
    assert limits["long"] == Decimal("400")
    result = allocation_guard(Decimal("1000"), Decimal("40"), Decimal("401"))
    assert result["allowed"] is False
    assert result["excess"] == Decimal("1")


def test_allocation_must_total_one_hundred():
    with pytest.raises(ValueError):
        allocation_limits(Decimal("1000"), Decimal("40"), Decimal("20"), Decimal("30"))
