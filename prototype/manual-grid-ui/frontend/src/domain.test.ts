import { describe, expect, it } from "vitest";
import { allocationLimits, guard, initialAccount, newOrder, prices, tpPrice } from "./domain";

describe("Manual Grid domain", () => {
  it("builds Long levels from current price and previous level", () => {
    const orders = [newOrder("long", 1), newOrder("long", 2)]; orders[0].offsetPct = 10; orders[1].offsetPct = 10;
    expect(prices(100, "long", orders)).toEqual([90, 81]);
  });
  it("uses live available margin for allocation", () => {
    expect(allocationLimits({...initialAccount, availableMargin: 1000}, {longPct:40,shortPct:20,reservePct:40}).long).toBe(400);
  });
  it("blocks when the full logical grid exceeds the side limit", () => {
    const orders = [newOrder("long", 1)]; orders[0].qty = 50000;
    expect(guard(initialAccount, {longPct:40,shortPct:20,reservePct:40}, "long", orders).allowed).toBe(false);
  });
  it("calculates Long TP above entry and Short TP below entry", () => {
    const long = newOrder("long", 1), short = newOrder("short", 1);
    expect(tpPrice(long, 100, {movePct:5, closePct:50})).toBe(105);
    expect(tpPrice(short, 100, {movePct:5, closePct:50})).toBe(95);
  });
});
