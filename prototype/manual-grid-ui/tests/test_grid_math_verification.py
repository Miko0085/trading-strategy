"""Golden/invariant verification for Generated Grid mathematics.

These tests intentionally encode the confirmed strategy math rather than the
implementation details:

Geometry:
    d_i = d_first + (d_last-d_first) * ((i-1)/(N-1))**K

Martingale:
    w_i = M**(i-1)
    normalized_weight_i = w_i / sum(w)

Restructuring invariants:
- reinvestment changes sizing/capital, not geometry;
- trailing changes pending geometry position, not the geometry curve itself;
- factual/locked entries are immutable under ordinary trailing;
- combined trailing + reinvestment composes the same two independent layers.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.shadow.engine import (
    apply_realized_execution,
    evaluate_restructuring,
    generate_grid,
    generate_side,
)
from app.shadow.geometry import distribution_vector, geometry_prices, geometry_proportions
from app.shadow.sizing import normalized_weights, planned_margin, quantity_for_budget
from app.shadow.trailing import trail_pending_grid


D = Decimal

FINE_INSTRUMENT = {
    "tick_size": "0.01",
    "qty_step": "0.000001",
    "min_order_qty": "0.000001",
    "min_notional_value": "0.01",
}


def account(
    available: str = "1000",
    *,
    mark: str = "100",
    long_upnl: str | None = None,
    short_upnl: str | None = None,
) -> dict[str, object]:
    return {
        "mark_price": mark,
        "wallet_balance": "1000",
        "equity": "1000",
        "available_margin": available,
        "realized_pnl": "0",
        "unrealized_pnl": "999",  # aggregate value must not drive side boosts
        "long_unrealized_pnl": long_upnl,
        "short_unrealized_pnl": short_upnl,
        "position_mode": "HEDGE",
    }


def configuration(*, short_enabled: bool = False) -> dict:
    side = {
        "enabled": True,
        "order_count": 10,
        "grid_depth_pct": "30",
        "first_order_offset_pct": "5",
        "distribution_coefficient": "1.5",
        "leverage": "2",
        "martingale_multiplier": "1.2",
        "active_order_count": 3,
        "tp_steps": [{"move_pct": "10", "close_pct": "50"}],
        "trailing_enabled": False,
        "realized_reinvest_pct": "0",
        "long_unrealized_reinvest_pct": "0",
        "short_unrealized_reinvest_pct": "0",
        "manual_overrides": [],
    }
    return {
        "symbol": "BTCUSDT",
        "allocation": {"long_pct": "30", "short_pct": "20", "reserve_pct": "20"},
        "long": dict(side),
        "short": {**side, "enabled": short_enabled},
    }


def prices(side_state: dict) -> list[Decimal]:
    return [D(str(order["entry_price"])) for order in side_state["orders"]]


def quantities(side_state: dict) -> list[Decimal]:
    return [D(str(order["qty"])) for order in side_state["orders"]]


def test_confirmed_power_distribution_matches_old_excel_golden_example():
    """Regression fixture from the previously reconstructed Veles-style sheet."""
    anchor = D("2650")
    first_offset = D("0.2")   # 2650 -> 2644.70
    depth = D("38")           # 2650 -> 1643.00
    count = 17
    coefficient = D("0.8")

    distances = distribution_vector(count, first_offset, depth, coefficient)
    generated = geometry_prices(anchor, "long", distances, D("0.01"))

    expected_first_five = [
        D("2644.70"),
        D("2535.70"),
        D("2454.91"),
        D("2382.19"),
        D("2314.26"),
    ]
    assert generated[:5] == expected_first_five
    assert generated[-1] == D("1643.00")
    assert len(generated) == 17


def test_power_distribution_boundary_and_coefficient_semantics():
    linear = distribution_vector(5, D("5"), D("30"), D("1"))
    concave = distribution_vector(5, D("5"), D("30"), D("0.8"))
    convex = distribution_vector(5, D("5"), D("30"), D("1.5"))

    assert linear == [D("5"), D("11.25"), D("17.5"), D("23.75"), D("30")]
    assert concave[0] == convex[0] == D("5")
    assert concave[-1] == convex[-1] == D("30")

    # K < 1 moves away from the first level faster.
    assert concave[1] > linear[1]
    # K > 1 keeps the first levels closer to the start and stretches the tail.
    assert convex[1] < linear[1]


@pytest.mark.parametrize("multiplier", [D("1"), D("1.2"), D("1.5")])
def test_martingale_is_exact_normalized_geometric_progression(multiplier: Decimal):
    weights = normalized_weights(8, multiplier)

    assert abs(sum(weights, D("0")) - D("1")) < D("1e-24")
    for left, right in zip(weights, weights[1:], strict=False):
        assert abs(right / left - multiplier) < D("1e-24")


def test_martingale_budget_changes_scale_sizing_without_changing_weights():
    prices_ = [D("95"), D("88"), D("80"), D("70")]
    leverage = D("2")
    step = D("0.000001")
    multiplier = D("1.2")
    expected_weights = normalized_weights(len(prices_), multiplier)

    small = quantity_for_budget(D("500"), prices_, leverage, step, step, multiplier)
    large = quantity_for_budget(D("750"), prices_, leverage, step, step, multiplier)

    assert planned_margin(prices_, small, leverage) <= D("500")
    assert planned_margin(prices_, large, leverage) <= D("750")

    # Recover per-level margin weights from quantities. Rounding is tiny because
    # qtyStep is intentionally fine in this verification fixture.
    small_margin = [p * q / leverage for p, q in zip(prices_, small, strict=True)]
    large_margin = [p * q / leverage for p, q in zip(prices_, large, strict=True)]
    small_total = sum(small_margin, D("0"))
    large_total = sum(large_margin, D("0"))

    for i, expected in enumerate(expected_weights):
        assert abs(small_margin[i] / small_total - expected) < D("0.00001")
        assert abs(large_margin[i] / large_total - expected) < D("0.00001")


def test_realized_reinvest_changes_sizing_but_never_geometry():
    cfg = configuration()
    cfg["long"]["realized_reinvest_pct"] = "50"

    initial = generate_grid(account=account(), configuration=cfg, instrument=FINE_INSTRUMENT)
    initial_side = initial["sides"]["long"]
    geometry_before = list(initial_side["geometry"]["distances_pct"])
    proportions_before = list(initial_side["geometry"]["proportions"])
    prices_before = prices(initial_side)
    qty_before = quantities(initial_side)

    # A factual profitable close grows the persistent Long StrategyDeposit by 50.
    after_profit = apply_realized_execution(
        initial,
        execution={
            "execution_id": "realized-1",
            "side": "Sell",
            "position_idx": 1,
            "trigger": "TP_FULL_FILL",
            "realized_pnl": "100",
            "fee": "0",
        },
        configuration=cfg,
    )
    assert after_profit["strategy_state"]["long_strategy_deposit"] == "350"

    revised = evaluate_restructuring(
        after_profit,
        trigger="CAPITAL_STATE_CHANGE",
        account=account(),
        configuration=cfg,
        instrument=FINE_INSTRUMENT,
    )["after"]
    revised_side = revised["sides"]["long"]

    assert revised_side["geometry"]["distances_pct"] == geometry_before
    assert revised_side["geometry"]["proportions"] == proportions_before
    assert prices(revised_side) == prices_before
    assert quantities(revised_side) != qty_before
    assert revised["strategy_state"]["long_strategy_deposit"] == "350"


def test_unrealized_reinvestment_is_temporary_and_does_not_move_geometry():
    cfg = configuration()
    cfg["long"]["long_unrealized_reinvest_pct"] = "10"

    initial = generate_grid(
        account=account(short_upnl="0"),
        configuration=cfg,
        instrument=FINE_INSTRUMENT,
    )
    before_side = initial["sides"]["long"]
    before_prices = prices(before_side)
    before_geometry = list(before_side["geometry"]["distances_pct"])

    boosted = evaluate_restructuring(
        initial,
        trigger="CAPITAL_STATE_CHANGE",
        account=account(short_upnl="500"),
        configuration=cfg,
        instrument=FINE_INSTRUMENT,
    )["after"]

    assert boosted["shadow_summary"]["long"]["current_unrealized_boost"] == "50"
    assert prices(boosted["sides"]["long"]) == before_prices
    assert boosted["sides"]["long"]["geometry"]["distances_pct"] == before_geometry

    # Floating PnL disappears: the temporary boost must disappear too, while
    # persistent StrategyDeposit and geometry stay unchanged.
    unboosted = evaluate_restructuring(
        boosted,
        trigger="CAPITAL_STATE_CHANGE",
        account=account(short_upnl="0"),
        configuration=cfg,
        instrument=FINE_INSTRUMENT,
    )["after"]

    assert unboosted["shadow_summary"]["long"]["current_unrealized_boost"] == "0"
    assert unboosted["strategy_state"]["long_strategy_deposit"] == initial["strategy_state"]["long_strategy_deposit"]
    assert prices(unboosted["sides"]["long"]) == before_prices
    assert unboosted["sides"]["long"]["geometry"]["distances_pct"] == before_geometry


def test_long_trailing_up_preserves_curve_and_reprices_only_eligible_pending_orders():
    side = generate_side(
        "long",
        anchor_price=D("100"),
        budget=D("300"),
        order_count=6,
        grid_depth_pct=D("30"),
        first_order_offset_pct=D("5"),
        distribution_coefficient=D("1.5"),
        leverage=D("2"),
        martingale_multiplier=D("1.2"),
        instrument=FINE_INSTRUMENT,
        active_order_count=3,
        tp_steps=[{"move_pct": "10", "close_pct": "50"}],
    )
    geometry_before = list(side["geometry"]["distances_pct"])
    proportions_before = list(side["geometry"]["proportions"])
    old_prices = prices(side)

    # Filled/partially-filled and manual-price-locked levels are factual/locked.
    side["orders"][1]["filled_qty"] = D("0.5")
    side["orders"][1]["actual_avg_fill"] = side["orders"][1]["entry_price"]
    side["orders"][2]["manual_price_lock"] = True

    trail_pending_grid(side, new_anchor=D("110"), tick_size=D("0.01"))

    assert side["geometry"]["distances_pct"] == geometry_before
    assert side["geometry"]["proportions"] == proportions_before
    assert side["anchor_price"] == D("110")
    assert side["orders"][1]["entry_price"] == old_prices[1]
    assert side["orders"][2]["entry_price"] == old_prices[2]

    expected = geometry_prices(D("110"), "long", geometry_before, D("0.01"))
    for index in (0, 3, 4, 5):
        assert side["orders"][index]["entry_price"] == expected[index]

    # Planned TP of a pending entry moves with the entry.
    first = side["orders"][0]
    assert D(str(first["planned_tp"][0]["price"])) == (
        D(str(first["entry_price"])) * D("1.10") / D("0.01")
    ).quantize(D("1")) * D("0.01")


def test_short_trailing_down_preserves_curve_and_reprices_pending_orders():
    side = generate_side(
        "short",
        anchor_price=D("100"),
        budget=D("200"),
        order_count=6,
        grid_depth_pct=D("30"),
        first_order_offset_pct=D("5"),
        distribution_coefficient=D("0.8"),
        leverage=D("2"),
        martingale_multiplier=D("1.2"),
        instrument=FINE_INSTRUMENT,
        active_order_count=3,
        tp_steps=[{"move_pct": "10", "close_pct": "50"}],
    )
    geometry_before = list(side["geometry"]["distances_pct"])
    old_prices = prices(side)

    trail_pending_grid(side, new_anchor=D("90"), tick_size=D("0.01"))

    assert side["geometry"]["distances_pct"] == geometry_before
    assert all(new < old for new, old in zip(prices(side), old_prices, strict=True))
    assert prices(side) == geometry_prices(D("90"), "short", geometry_before, D("0.01"))


def test_combined_trailing_and_realized_reinvest_composes_geometry_and_sizing():
    cfg = configuration()
    cfg["long"]["realized_reinvest_pct"] = "50"

    current = generate_grid(account=account(), configuration=cfg, instrument=FINE_INSTRUMENT)
    geometry_before = list(current["sides"]["long"]["geometry"]["distances_pct"])
    qty_before = quantities(current["sides"]["long"])

    current = apply_realized_execution(
        current,
        execution={
            "execution_id": "realized-combined-1",
            "side": "Sell",
            "position_idx": 1,
            "trigger": "TP_PARTIAL_FILL",
            "realized_pnl": "100",
            "fee": "0",
        },
        configuration=cfg,
    )

    cfg["long"]["anchor_price"] = "110"
    result = evaluate_restructuring(
        current,
        trigger="TRAILING_TRIGGER",
        account=account(mark="110"),
        configuration=cfg,
        instrument=FINE_INSTRUMENT,
    )["after"]
    side = result["sides"]["long"]

    assert result["strategy_state"]["long_strategy_deposit"] == "350"
    assert side["anchor_price"] == D("110")
    assert side["geometry"]["distances_pct"] == geometry_before
    assert prices(side) == geometry_prices(D("110"), "long", geometry_before, D("0.01"))
    assert quantities(side) != qty_before
    assert side["planned_margin"] <= side["budget"]


@pytest.mark.parametrize("count", [2, 3, 10, 20, 50])
@pytest.mark.parametrize("coefficient", [D("0.2"), D("0.8"), D("1"), D("1.5"), D("3")])
@pytest.mark.parametrize("multiplier", [D("1"), D("1.05"), D("1.2"), D("1.5"), D("2")])
def test_grid_math_invariants_across_parameter_matrix(count: int, coefficient: Decimal, multiplier: Decimal):
    first = D("2")
    depth = D("45")
    anchor = D("100")
    distances = distribution_vector(count, first, depth, coefficient)

    assert len(distances) == count
    assert distances[0] == first
    assert distances[-1] == depth
    assert all(left < right for left, right in zip(distances, distances[1:], strict=False))

    long_prices = geometry_prices(anchor, "long", distances, D("0.0001"))
    short_prices = geometry_prices(anchor, "short", distances, D("0.0001"))
    assert all(left > right for left, right in zip(long_prices, long_prices[1:], strict=False))
    assert all(left < right for left, right in zip(short_prices, short_prices[1:], strict=False))

    proportions = geometry_proportions(distances)
    assert proportions[-1] == D("1")

    weights = normalized_weights(count, multiplier)
    assert abs(sum(weights, D("0")) - D("1")) < D("1e-24")
    for left, right in zip(weights, weights[1:], strict=False):
        assert abs(right / left - multiplier) < D("1e-24")

    qty = quantity_for_budget(
        D("1000"),
        long_prices,
        D("3"),
        D("0.000001"),
        D("0.000001"),
        multiplier,
    )
    assert all(value >= D("0") for value in qty)
    assert planned_margin(long_prices, qty, D("3")) <= D("1000")
