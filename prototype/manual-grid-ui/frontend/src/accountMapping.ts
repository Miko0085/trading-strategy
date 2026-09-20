import { AccountState, Side } from "./domain";
import { AccountApiResponse } from "./types";

const numberOrNull = (value: unknown): number | null => value == null ? null : Number(value);

export function normalizeAccountResponse(data: AccountApiResponse, current: AccountState): AccountState {
  const position = (value: Record<string, unknown> | null | undefined) => value ? ({
    side: value.side as Side,
    size: numberOrNull(value.size),
    avgEntryPrice: numberOrNull(value.avg_entry_price),
    unrealizedPnl: numberOrNull(value.unrealized_pnl),
    leverage: numberOrNull(value.leverage),
    initialMargin: numberOrNull(value.initial_margin),
    maintenanceMargin: numberOrNull(value.maintenance_margin),
    notional: numberOrNull(value.notional),
  }) : null;
  const openOrders = ((data.orders as Array<Record<string, unknown>> | undefined) || []).map((item) => ({
    orderId: typeof item.order_id === "string" ? item.order_id : null,
    side: typeof item.side === "string" ? item.side : null,
    status: typeof item.status === "string" ? item.status : null,
    price: numberOrNull(item.price),
    qty: numberOrNull(item.qty),
    leavesQty: numberOrNull(item.leaves_qty),
  }));
  return {
    ...current,
    markPrice: numberOrNull(data.mark_price),
    availableMargin: numberOrNull(data.available_margin),
    equity: numberOrNull(data.equity),
    walletBalance: numberOrNull(data.wallet_balance),
    initialMargin: numberOrNull(data.initial_margin),
    maintenanceMargin: numberOrNull(data.maintenance_margin),
    grossExposure: numberOrNull(data.gross_exposure),
    netExposure: numberOrNull(data.net_exposure),
    longPosition: position(data.long),
    shortPosition: position(data.short),
    openOrders,
    ordersAvailable: data.orders_available !== false,
    ordersError: data.orders_error || null,
    instrument: data.instrument ? {
      symbol: data.instrument.symbol,
      tickSize: numberOrNull(data.instrument.tick_size),
      qtyStep: numberOrNull(data.instrument.qty_step),
      minOrderQty: numberOrNull(data.instrument.min_order_qty),
      minNotionalValue: numberOrNull(data.instrument.min_notional_value),
    } : null,
    source: data.source || current.source,
    stale: Boolean(data.stale),
    error: data.error || undefined,
    updatedAt: data.updated_at || null,
  };
}
