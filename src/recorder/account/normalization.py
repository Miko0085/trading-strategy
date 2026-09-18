"""Official reported amounts as decimal strings. Missing is NULL, never guessed zero."""


def amount(item, name):
    value = item.get(name)
    return str(value) if value not in (None, "") else None


def persist_financial(store, observation_id, kind, item, stamp):
    if kind == "WALLET":
        fields = (
            "totalWalletBalance",
            "totalEquity",
            "totalAvailableBalance",
            "totalPerpUPL",
            "totalInitialMargin",
            "totalMaintenanceMargin",
        )
        store.db.execute(
            "INSERT INTO account_balances VALUES(?,?,?,?,?,?,?,?)",
            (observation_id, item.get("accountType"), *(amount(item, f) for f in fields)),
        )
        for coin in item.get("coin", []):
            store.db.execute(
                "INSERT INTO coin_balances VALUES(?,?,?,?,?,?)",
                (
                    observation_id,
                    coin["coin"],
                    *(
                        amount(coin, f)
                        for f in ("walletBalance", "equity", "unrealisedPnl", "cumRealisedPnl")
                    ),
                ),
            )
    elif kind == "POSITION":
        store.db.execute(
            "INSERT INTO position_balances VALUES(?,?,?,?,?,?,?,?,?)",
            (
                observation_id,
                item.get("symbol"),
                item.get("positionIdx"),
                item.get("side"),
                *(
                    amount(item, f)
                    for f in (
                        "size",
                        "entryPrice",
                        "unrealisedPnl",
                        "curRealisedPnl",
                        "cumRealisedPnl",
                    )
                ),
            ),
        )
    elif kind in {"CLOSED_PNL", "FUNDING"}:
        store.db.execute(
            "INSERT INTO pnl_records VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                observation_id,
                kind,
                item.get("symbol"),
                item.get("id") or item.get("orderId"),
                item.get("currency"),
                amount(item, "closedPnl"),
                amount(item, "funding"),
                amount(item, "cashFlow"),
                amount(item, "fee"),
                stamp,
            ),
        )
