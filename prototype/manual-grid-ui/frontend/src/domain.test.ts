import { describe, expect, it } from "vitest";
import { allocationLimits, guard, initialAccount, newOrder, prices, tpPrice } from "./domain";

describe("Manual Grid domain", () => {
  it("builds Long levels from current price and previous level", () => {
    const orders = [newOrder("long", 1), newOrder("long", 2)]; orders[0].offsetPct = 10; orders[1].offsetPct = 10;
    expect(prices(100, "long", orders, 0.1)).toEqual([90, 81]);
  });
  it("uses live available margin for allocation", () => {
    expect(allocationLimits({...initialAccount, availableMargin: 1000}, {longPct:40,shortPct:20,reservePct:40}).long).toBe(400);
  });
  it("blocks when the full logical grid exceeds the side limit", () => {
    const orders = [newOrder("long", 1)]; orders[0].qty = 50000;
    const account = {...initialAccount, availableMargin: 10000, markPrice: 100, instrument: {tickSize: 0.1, qtyStep: 1, minOrderQty: 1, minNotionalValue: 5}};
    expect(guard(account, {longPct:40,shortPct:20,reservePct:40}, "long", orders, 0.1, 2).allowed).toBe(false);
  });
  it("calculates Long TP above entry and Short TP below entry", () => {
    const long = newOrder("long", 1), short = newOrder("short", 1);
    expect(tpPrice(long, 100, {movePct:5, closePct:50}, 0.1)).toBe(105);
    expect(tpPrice(short, 100, {movePct:5, closePct:50}, 0.1)).toBe(95);
  });
});
