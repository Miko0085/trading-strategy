import { describe, expect, it } from "vitest";
import { generatedOrdersToGrid } from "./generatedMapping";

const orders = [
  { level: 1, entry_price: "90", qty: "2", filled_qty: "0", actual_avg_fill: null, planned_tp: [{ move_pct: "10", close_pct: "50" }], source: "ALGORITHM", manual_price_lock: false, manual_qty_lock: false, validation_errors: [] },
  { level: 2, entry_price: "81", qty: "3", filled_qty: "1", actual_avg_fill: "80", planned_tp: [{ move_pct: "20", close_pct: "25" }], source: "MANUAL_OVERRIDE", manual_price_lock: true, manual_qty_lock: true, validation_errors: [] },
];

describe("generated grid mapping", () => {
  it("converts generated absolute entries to working-grid offsets", () => {
    const result = generatedOrdersToGrid("long", orders, 100);
    expect(result.map((order) => order.offsetPct)).toEqual([10, 10]);
    expect(result.map((order) => order.calculatedEntryPrice)).toEqual([90, 81]);
  });

  it("copies fills, TP templates and override metadata", () => {
    const result = generatedOrdersToGrid("short", orders, 100);
    expect(result[1]).toMatchObject({ source: "GENERATED_ALGORITHM", filledQty: 1, avgFill: 80, qty: 3 });
    expect(result[0].tps).toEqual([{ movePct: 10, closePct: 50 }]);
    expect(result[1].manualOverrideMetadata).toMatchObject({ source: "MANUAL_OVERRIDE", manualPriceLock: true, manualQtyLock: true });
  });

  it("does not make any exchange call or mutate the preview input", () => {
    const before = JSON.stringify(orders);
    generatedOrdersToGrid("long", orders, 100);
    expect(JSON.stringify(orders)).toBe(before);
  });
});
