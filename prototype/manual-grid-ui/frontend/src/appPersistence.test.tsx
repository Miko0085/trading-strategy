/** @vitest-environment jsdom */
import { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./main";
import { emptyDraft, loadDraft, saveDraft, setSelectedSymbol } from "./workspaceStorage";

Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });

function apiResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

function mockApi(): void {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const path = String(input);
    if (path.includes("/api/health")) return Promise.resolve(apiResponse({ status: "ok", private_integration: true, read_only: true, environment: "mainnet", credential_source: "root_env", account_state_ready: true, orders_ready: true, private_state_ready: true }));
    if (path.includes("/api/symbols")) return Promise.resolve(apiResponse({ symbols: ["BTCUSDT", "ETHUSDT", "XRPUSDT"] }));
    if (path.includes("/api/state/")) return Promise.resolve(apiResponse({ source: "bybit_read_only", stale: false, mark_price: "2000", wallet_balance: "100", equity: "100", available_margin: "80", updated_at: "2026-09-20T00:00:00Z", instrument: { symbol: "ETHUSDT", tick_size: "0.1", qty_step: "0.1", min_order_qty: "0.1", min_notional_value: "5" }, orders: [] }));
    return Promise.resolve(apiResponse({ symbols: [] }));
  }));
}

async function mountApp(): Promise<{ root: Root; container: HTMLDivElement }> {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => { root.render(<App/>); await Promise.resolve(); });
  return { root, container };
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
  window.localStorage.clear();
});

describe("App local draft remount", () => {
  it("opens the persisted symbol and restores its grid after a remount", async () => {
    mockApi();
    const draft = emptyDraft();
    draft.allocation = { longPct: 40, shortPct: 20, reservePct: 40 };
    draft.long = [{ id: "eth-level-1", side: "long", level: 1, offsetPct: 10, qty: 1, filledQty: 0, avgFill: null, tps: [], note: "ETH draft" }];
    expect(saveDraft("ETHUSDT", draft).ok).toBe(true);
    expect(setSelectedSymbol("ETHUSDT").ok).toBe(true);

    const first = await mountApp();
    expect(first.container.querySelector<HTMLInputElement>("input[role=combobox]")?.value).toBe("ETHUSDT");
    expect(first.container.textContent).toContain("1 уровней");
    await act(async () => first.root.unmount());

    const second = await mountApp();
    expect(second.container.querySelector<HTMLInputElement>("input[role=combobox]")?.value).toBe("ETHUSDT");
    expect(second.container.textContent).toContain("1 уровней");
    expect(second.container.querySelector<HTMLInputElement>('.allocation-panel input[type="number"]')?.value).toBe("40");
    await act(async () => second.root.unmount());
  });

  it("writes the latest draft synchronously on pagehide", async () => {
    mockApi();
    const draft = emptyDraft();
    draft.allocation = { longPct: 40, shortPct: 20, reservePct: 40 };
    saveDraft("ETHUSDT", draft);
    setSelectedSymbol("ETHUSDT");
    const mounted = await mountApp();
    const longAllocation = mounted.container.querySelector<HTMLInputElement>('.allocation-panel input[type="number"]');
    expect(longAllocation).not.toBeNull();
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
      setter?.call(longAllocation, "55");
      longAllocation?.dispatchEvent(new Event("input", { bubbles: true }));
      window.dispatchEvent(new Event("pagehide"));
    });
    expect(loadDraft("ETHUSDT")?.allocation.longPct).toBe(55);
    await act(async () => mounted.root.unmount());
  });
});
