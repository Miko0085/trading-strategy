import { describe, expect, it, vi } from "vitest";
import { apiUrl, fetchJson, ApiError } from "./api";
import { normalizeAccountResponse } from "./accountMapping";
import { initialAccount } from "./domain";

describe("frontend API boundary", () => {
  it("uses a relative URL by default", () => {
    expect(apiUrl("/api/health")).toBe("/api/health");
  });

  it("maps real account fields without substituting fixtures", () => {
    const account = normalizeAccountResponse({ source: "bybit_read_only", stale: false, mark_price: "80360.04", wallet_balance: "107.979", equity: "116.738", available_margin: "81.285", updated_at: "2026-09-20T00:00:00Z", instrument: { symbol: "BTCUSDT", tick_size: "0.1", qty_step: "0.001", min_order_qty: "0.001", min_notional_value: "5" }, orders: [] }, initialAccount);
    expect(account.source).toBe("bybit_read_only");
    expect(account.markPrice).toBeCloseTo(80360.04);
    expect(account.walletBalance).toBeCloseTo(107.979);
    expect(account.availableMargin).toBeCloseTo(81.285);
    expect(account.equity).toBeCloseTo(116.738);
  });

  it("keeps missing factual values as null", () => {
    const account = normalizeAccountResponse({ source: "public_only", stale: true, orders: [] }, initialAccount);
    expect(account.markPrice).toBeNull();
    expect(account.availableMargin).toBeNull();
    expect(account.walletBalance).toBeNull();
  });

  it("exposes failed state requests as safe visible errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Bybit state is unavailable" }), { status: 502, headers: { "Content-Type": "application/json" } })));
    await expect(fetchJson("/api/state/BTCUSDT")).rejects.toMatchObject({ status: 502, errorType: "http_error" } satisfies Partial<ApiError>);
    vi.unstubAllGlobals();
  });
});
