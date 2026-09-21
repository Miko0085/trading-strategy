import { GridOrder, Side, TP, uid } from "./domain";
import { ShadowProposal } from "./shadowTypes";

type GeneratedOrder = ShadowProposal["sides"][string]["orders"][number];

function numberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function offsetFromEntry(previous: number | null, entry: number | null, side: Side): number | null {
  if (previous == null || entry == null || previous === 0) return null;
  const direction = side === "long" ? previous - entry : entry - previous;
  return direction > 0 ? direction / previous * 100 : null;
}

export function generatedOrdersToGrid(side: Side, orders: GeneratedOrder[], markPrice: number | null): GridOrder[] {
  let previous = markPrice;
  return orders.map((order) => {
    const entry = numberOrNull(order.entry_price);
    const mapped: GridOrder = {
      id: uid(), side, level: order.level, offsetPct: offsetFromEntry(previous, entry, side), qty: numberOrNull(order.qty),
      filledQty: numberOrNull(order.filled_qty) ?? 0, avgFill: numberOrNull(order.actual_avg_fill),
      tps: (order.planned_tp ?? []).map((tp): TP => ({ movePct: numberOrNull(tp.move_pct), closePct: numberOrNull(tp.close_pct) })),
      note: "", source: "GENERATED_ALGORITHM", calculatedEntryPrice: entry,
      manualOverrideMetadata: { source: order.source ?? "ALGORITHM", manualPriceLock: Boolean(order.manual_price_lock), manualQtyLock: Boolean(order.manual_qty_lock) },
    };
    previous = entry;
    return mapped;
  });
}
