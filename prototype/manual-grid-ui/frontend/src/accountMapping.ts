import { AccountState } from "./domain";

const numberOrNull = (value: unknown): number | null => value == null ? null : Number(value);

export function normalizeAccountResponse(data: any, current: AccountState): AccountState {
  const position = (value: any) => value ? ({
    side: value.side,
    size: numberOrNull(value.size),
    avgEntryPrice: numberOrNull(value.avg_entry_price),
    unrealizedPnl: numberOrNull(value.unrealized_pnl),
    leverage: numberOrNull(value.leverage),
    initialMargin: numberOrNull(value.initial_margin),
    maintenanceMargin: numberOrNull(value.maintenance_margin),
    notional: numberOrNull(value.notional),
  }) : null;
  const openOrders = (data.orders || []).map((item: any) => ({
    orderId: item.order_id ?? null,
    side: item.side ?? null,
    status: item.status ?? null,
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
    instrument: data.instrument ? {
      symbol: data.instrument.symbol,
      tickSize: numberOrNull(data.instrument.tick_size),
      qtyStep: numberOrNull(data.instrument.qty_step),
      minOrderQty: numberOrNull(data.instrument.min_order_qty),
      minNotionalValue: numberOrNull(data.instrument.min_notional_value),
    } : null,
    source: data.source,
    stale: Boolean(data.stale),
    error: data.error || undefined,
    updatedAt: data.updated_at || null,
  };
}
