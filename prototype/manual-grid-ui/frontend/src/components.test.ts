import { describe, expect, it } from "vitest";
import { initialAccount, newOrder } from "./domain";
import { ladderPrices } from "./components/PriceLadder";
import { riskMeterModel } from "./components/UtilizationGauge";
import { connectionStatus, stateOrdersMessage } from "./components/StateView";
import { orderDisplayModel } from "./components/GridOrderCard";
import { tpDisplayModel } from "./components/TakeProfitEditor";
import { moveHighlight } from "./components/SymbolSelector";

describe("risk meter and factual state", () => {
  it("stays neutral and visible before calculation", () => {
    expect(riskMeterModel()).toEqual({ state: "neutral", utilization: "—", limit: "—", activeWindow: "—", queue: "—", fullGrid: "—", remaining: "—", excess: "—" });
  });

  it("shows utilization and exact excess in blocked state", () => {
    const result = riskMeterModel({ side: "long", orders: [], active_window_levels: [], queued_levels: [], full_grid_planned_margin: 120, active_window_planned_margin: 120, queued_planned_margin: 0, planned_qty: 1, planned_average: 1, aggregate_tp_gross_pnl: 0, aggregate_fee_estimate: null, aggregate_net_pnl: null, allocation_limit: 100, remaining_limit: -20, utilization_pct: 120, excess: 20, validation_errors: [], status: "BLOCKED" });
    expect(result.state).toBe("danger");
    expect(result.utilization).toContain("120");
    expect(result.excess).toContain("20");
  });

  it("keeps the meter gradient active when validation is blocked for another reason", () => {
    const result = riskMeterModel({ side: "long", orders: [], active_window_levels: [], queued_levels: [], full_grid_planned_margin: 40, active_window_planned_margin: 40, queued_planned_margin: 0, planned_qty: 1, planned_average: 1, aggregate_tp_gross_pnl: 0, aggregate_fee_estimate: null, aggregate_net_pnl: null, allocation_limit: 100, remaining_limit: 60, utilization_pct: 40, excess: null, validation_errors: [{ level: 1, errors: ["qty must be >= minOrderQty"] }], status: "BLOCKED" });
    expect(result.state).toBe("ok");
    expect(result.utilization).toContain("40");
    expect(result.excess).toBe("—");
  });

  it("describes empty and unavailable exchange orders distinctly", () => {
    expect(stateOrdersMessage({ ...initialAccount, ordersAvailable: true, openOrders: [] })).toBe("Активных ордеров нет");
    expect(stateOrdersMessage({ ...initialAccount, ordersAvailable: false, ordersError: "safe error" })).toBe("Не удалось получить активные ордера Bybit");
  });

  it("keeps account connectivity separate from open-order availability", () => {
    expect(connectionStatus(true, false, true)).toContain("Bybit account подключён");
    expect(connectionStatus(true, false, true)).toContain("ордера временно недоступны");
    expect(connectionStatus(false, false, true)).toBe("Приватные данные Bybit недоступны");
  });
});

describe("selector and price ladder behavior", () => {
  it("supports bounded keyboard navigation", () => {
    expect(moveHighlight(0, "ArrowDown", 3)).toBe(1);
    expect(moveHighlight(2, "ArrowDown", 3)).toBe(2);
    expect(moveHighlight(1, "ArrowUp", 3)).toBe(0);
    expect(moveHighlight(0, "Escape", 3)).toBe(0);
  });

  it("uses backend planned prices when calculation is present", () => {
    const order = newOrder("long", 1);
    order.offsetPct = 10;
    const calculation = { symbol: "BTCUSDT", mark_price: 100, available_margin: 1000, fee_rate: null, long: { side: "long" as const, orders: [{ level: 1, planned_entry_price: 77, configured_qty: 1, notional: 77, planned_margin: 77, cumulative_planned_average: 77, planned_tp_qty: 0, planned_remaining_after_all_tp: 1, tp_steps: [], validation_errors: [], status: "VALID" as const }], active_window_levels: [1], queued_levels: [], full_grid_planned_margin: 77, active_window_planned_margin: 77, queued_planned_margin: 0, planned_qty: 1, planned_average: 77, aggregate_tp_gross_pnl: 0, aggregate_fee_estimate: null, aggregate_net_pnl: null, allocation_limit: 100, remaining_limit: 23, utilization_pct: 77, excess: null, validation_errors: [], status: "VALID" as const }, short: { side: "short" as const, orders: [], active_window_levels: [], queued_levels: [], full_grid_planned_margin: 0, active_window_planned_margin: 0, queued_planned_margin: 0, planned_qty: 0, planned_average: null, aggregate_tp_gross_pnl: 0, aggregate_fee_estimate: null, aggregate_net_pnl: null, allocation_limit: 0, remaining_limit: 0, utilization_pct: 0, excess: null, validation_errors: [], status: "VALID" as const }, combined_planned_margin: 77, combined_gross_pnl: 0, combined_fee_estimate: null, combined_net_pnl: null, validation_state: "VALID" as const };
    expect(ladderPrices({ ...initialAccount, markPrice: 100 }, [order], [], 0.1, calculation).long).toEqual([77]);
  });

  it("marks order and TP values as Preview until backend data exists", () => {
    const order = newOrder("long", 1);
    order.qty = 1;
    const preview = orderDisplayModel(order, 90, undefined, 2);
    expect(preview.badge).toBe("Preview");
    expect(preview.price).toBe(90);
    const tp = { movePct: 2, closePct: 25 };
    const tpPreview = tpDisplayModel(order, 90, tp, 0.1);
    expect(tpPreview.badge).toBe("Preview");
    expect(tpPreview.fee).toBeNull();
    const tpBackend = tpDisplayModel(order, 90, tp, 0.1, { price: 95, qty: 0.25, close_pct: 25, gross_pnl: 1.25, fee: 0.1, net_pnl: 1.15, basis: "planned_entry" });
    expect(tpBackend.badge).toBe("Backend");
    expect(tpBackend.price).toBe(95);
    expect(tpBackend.netPnl).toBe(1.15);
  });
});
