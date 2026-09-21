from __future__ import annotations

from decimal import Decimal
from typing import Any


def pick(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def normalize_instrument(result: dict[str, Any]) -> dict[str, Any]:
    item = (result.get("list") or [{}])[0]
    lot = item.get("lotSizeFilter") or {}
    price = item.get("priceFilter") or {}
    return {"symbol": item.get("symbol"), "tick_size": pick(price, "tickSize"), "qty_step": pick(lot, "qtyStep"), "min_order_qty": pick(lot, "minOrderQty"), "min_notional_value": pick(lot, "minNotionalValue")}


def normalize_positions(result: dict[str, Any], mark_price: str | None) -> list[dict[str, Any]]:
    normalized = []
    for item in result.get("list", []):
        position_idx = str(item.get("positionIdx", ""))
        raw_side = item.get("side")
        side = "long" if raw_side in ("Buy", "Long") or position_idx == "1" else "short" if raw_side in ("Sell", "Short") or position_idx == "2" else None
        if side is None:
            continue
        size = pick(item, "size")
        notional = str(Decimal(str(mark_price)) * Decimal(str(size))) if mark_price is not None and size is not None else None
        normalized.append({"side": side, "symbol": item.get("symbol"), "size": size, "avg_entry_price": pick(item, "avgPrice", "avgEntryPrice"), "unrealized_pnl": pick(item, "unrealisedPnl", "unrealizedPnl"), "leverage": item.get("leverage"), "initial_margin": pick(item, "positionIM", "positionIm"), "maintenance_margin": pick(item, "positionMM", "positionMm"), "notional": notional, "position_idx": item.get("positionIdx")})
    return normalized


def normalize_position_mode(result: dict[str, Any]) -> str:
    """Infer the symbol mode from Bybit's factual positionIdx values.

    Bybit uses positionIdx=0 for one-way and 1/2 for hedge. With no rows
    there is no safe read-only proof of the symbol mode, so keep it unknown.
    """
    rows = result.get("list", [])
    indices = {str(item.get("positionIdx")) for item in rows if item.get("positionIdx") is not None}
    if indices & {"1", "2"}:
        return "HEDGE"
    if indices and indices <= {"0"}:
        return "ONE_WAY"
    return "UNKNOWN"


def normalize_orders(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"order_id": item.get("orderId"), "symbol": item.get("symbol"), "side": item.get("side"), "status": item.get("orderStatus"), "price": item.get("price"), "qty": item.get("qty"), "leaves_qty": item.get("leavesQty"), "position_idx": item.get("positionIdx")} for item in result.get("list", [])]


def normalize_executions(result: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = []
    seen: set[str] = set()
    for item in result.get("list", []):
        execution_id = item.get("execId")
        if execution_id and execution_id in seen:
            continue
        if execution_id:
            seen.add(execution_id)
        normalized.append({"execution_id": execution_id, "order_id": item.get("orderId"), "symbol": item.get("symbol"), "side": item.get("side"), "price": item.get("execPrice"), "qty": item.get("execQty"), "fee": item.get("execFee"), "timestamp": item.get("execTime"), "realized_pnl": item.get("execPnl"), "position_idx": item.get("positionIdx")})
    return normalized


def normalize_account(wallet: dict[str, Any], positions: dict[str, Any], orders: dict[str, Any], ticker: dict[str, Any], instrument: dict[str, Any], source: str, executions: dict[str, Any] | None = None) -> dict[str, Any]:
    account = (wallet.get("list") or [{}])[0]
    ticker_row = (ticker.get("list") or [{}])[0]
    mark = pick(ticker_row, "markPrice", "lastPrice")
    position_rows = normalize_positions(positions, mark)
    long_position = next((item for item in position_rows if item["side"] == "long"), None)
    short_position = next((item for item in position_rows if item["side"] == "short"), None)
    long_size = Decimal(str(long_position["size"])) if long_position and long_position["size"] is not None else None
    short_size = Decimal(str(short_position["size"])) if short_position and short_position["size"] is not None else None
    gross = Decimal(str(mark)) * (long_size + short_size) if mark is not None and long_size is not None and short_size is not None else None
    net = Decimal(str(mark)) * (long_size - short_size) if mark is not None and long_size is not None and short_size is not None else None
    long_unrealized = long_position.get("unrealized_pnl") if long_position else None
    short_unrealized = short_position.get("unrealized_pnl") if short_position else None
    unrealized = pick(account, "totalPerpUPL", "totalUnrealisedPnl", "totalUnrealizedPnl")
    return {"source": source, "symbol": ticker_row.get("symbol") or instrument.get("symbol"), "mark_price": mark, "wallet_balance": pick(account, "totalWalletBalance"), "equity": pick(account, "totalEquity"), "available_margin": pick(account, "totalAvailableBalance"), "initial_margin": pick(account, "totalInitialMargin"), "maintenance_margin": pick(account, "totalMaintenanceMargin"), "realized_pnl": pick(account, "totalRealisedPnl", "totalRealizedPnl"), "unrealized_pnl": unrealized, "long_unrealized_pnl": long_unrealized, "short_unrealized_pnl": short_unrealized, "positions": position_rows, "long": long_position, "short": short_position, "gross_exposure": str(gross) if gross is not None else None, "net_exposure": str(net) if net is not None else None, "orders": normalize_orders(orders), "executions": normalize_executions(executions or {}), "instrument": instrument, "position_mode": normalize_position_mode(positions), "position_mode_symbol": ticker_row.get("symbol") or instrument.get("symbol")}
