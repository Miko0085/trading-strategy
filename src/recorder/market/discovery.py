"""Persistent instrument discovery, independent of the permanent market watchlist."""

import json
from datetime import UTC, datetime


def track(store, category, symbol, source, received, raw_id=None):
    if not symbol:
        return False
    inserted = (
        store.db.execute(
            "INSERT OR IGNORE INTO tracked_instruments(category,symbol,first_seen,source,raw_id) VALUES(?,?,?,?,?)",
            (category, symbol, received, source, raw_id),
        ).rowcount
        == 1
    )
    if inserted and source != "configured":
        store.gap(
            "market_before_discovery",
            f"{category}/{symbol}: exact market quotes before discovery are unavailable",
        )
    if not inserted:
        # New account activity for a previously stopped symbol resumes market coverage.
        store.db.execute(
            "UPDATE tracked_instruments SET stopped_at=NULL WHERE category=? AND symbol=? AND stopped_at IS NOT NULL",
            (category, symbol),
        )
    return inserted


def stop_tracking(store, category, symbol, when):
    """Stop live market coverage for a flat symbol; the registry row is kept, not deleted."""
    store.db.execute(
        "UPDATE tracked_instruments SET stopped_at=? WHERE category=? AND symbol=? AND stopped_at IS NULL",
        (when, category, symbol),
    )


def is_flat(store, symbol):
    """True only once an observed position confirms zero size and no active orders.

    Absence of any position observation is treated as unknown, not flat: a symbol
    just discovered via an order/execution/closed_pnl event may not have a
    POSITION snapshot yet, and stopping coverage before that would be a guess.
    """
    positions = store.db.execute(
        "SELECT data_json FROM current_states WHERE kind='POSITION' AND symbol=?", (symbol,)
    ).fetchall()
    if not positions:
        return False
    if any(float(json.loads(row[0]).get("size") or 0) != 0 for row in positions):
        return False
    active_statuses = {"New", "PartiallyFilled", "Untriggered"}
    orders = store.db.execute(
        "SELECT data_json FROM current_states WHERE kind='ORDER' AND symbol=?", (symbol,)
    ).fetchall()
    return not any(json.loads(row[0]).get("orderStatus") in active_statuses for row in orders)


def bootstrap(store, category, configured):
    """Rehydrate from existing normalized data; never delete records or note links."""
    with store.transaction():
        received = datetime.now(UTC).isoformat()
        for symbol in configured:
            track(store, category, symbol, "configured", received)
        for table in ("orders", "executions", "positions", "closed_pnl", "funding"):
            for row in store.db.execute(
                f"SELECT symbol,raw_json FROM {table} WHERE symbol IS NOT NULL"
            ):
                data = json.loads(row[1])
                track(
                    store, data.get("category") or category, row[0], "legacy_normalized", received
                )


def tracked_symbols(store, category):
    return [
        r[0]
        for r in store.db.execute(
            "SELECT symbol FROM tracked_instruments WHERE category=? AND stopped_at IS NULL ORDER BY symbol",
            (category,),
        )
    ]
