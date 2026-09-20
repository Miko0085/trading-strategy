export type Side = "long" | "short";
export type TP = { movePct: number; closePct: number };
export type GridOrder = { id: string; side: Side; level: number; offsetPct: number; qty: number; filledQty: number; avgFill: number | null; tps: TP[]; note: string };
export type AccountState = { symbol: string; markPrice: number; availableMargin: number; equity: number; walletBalance: number; initialMargin: number; maintenanceMargin: number; updatedAt: string; source: string };
export type Allocation = { longPct: number; shortPct: number; reservePct: number };
export const limits = { tickSize: 0.0001, minQty: 1, qtyStep: 1, minNotional: 5, leverage: 3, feeRate: 0.00055 };
export const initialAccount: AccountState = { symbol: "UAIUSDT", markPrice: 0.3996, availableMargin: 10000, equity: 10000, walletBalance: 10000, initialMargin: 0, maintenanceMargin: 0, updatedAt: new Date().toISOString(), source: "demo" };
export const uid = () => Math.random().toString(36).slice(2, 10);
export function newOrder(side: Side, level: number): GridOrder { return { id: uid(), side, level, offsetPct: level === 1 ? 5 : 8, qty: level === 1 ? 100 : 150, filledQty: 0, avgFill: null, tps: [{ movePct: 2, closePct: 50 }], note: "" }; }
export function prices(mark: number, side: Side, orders: GridOrder[]): number[] { let previous = mark; return orders.map((o) => { previous = round(previous * (side === "long" ? 1 - o.offsetPct / 100 : 1 + o.offsetPct / 100)); return previous; }); }
export function round(value: number): number { return Math.round(value / limits.tickSize) * limits.tickSize; }
export function allocationLimits(account: AccountState, allocation: Allocation) { return { long: account.availableMargin * allocation.longPct / 100, short: account.availableMargin * allocation.shortPct / 100, reserve: account.availableMargin * allocation.reservePct / 100 }; }
export function margin(order: GridOrder, price: number): number { return price * order.qty / limits.leverage; }
export function tpPrice(order: GridOrder, price: number, tp: TP): number { return round(price * (order.side === "long" ? 1 + tp.movePct / 100 : 1 - tp.movePct / 100)); }
export function pnl(order: GridOrder, entry: number, tp: TP): number { const qty = order.filledQty || order.qty; return (tpPrice(order, entry, tp) - entry) * qty * (order.side === "long" ? 1 : -1); }
export function guard(account: AccountState, allocation: Allocation, side: Side, orders: GridOrder[]) { const limit = allocationLimits(account, allocation)[side]; const planned = orders.reduce((sum, o, i) => sum + margin(o, prices(account.markPrice, side, orders)[i]), 0); return { limit, planned, remaining: limit - planned, allowed: planned <= limit }; }
