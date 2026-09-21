/** @vitest-environment jsdom */
import { afterEach, describe, expect, it } from "vitest";
import { emptyDraft, loadDraft, loadWorkspace, removeDraft, saveDraft, setSelectedSymbol, storageDiagnostic, WORKSPACE_STORAGE_KEY } from "./workspaceStorage";

afterEach(() => window.localStorage.clear());

describe("local workspace storage", () => {
  it("stores a versioned workspace and isolates drafts by symbol", () => {
    const btc = emptyDraft(); btc.long = [{ id: "btc-1", side: "long", level: 1, offsetPct: 5, qty: 0.1, filledQty: 0, avgFill: null, tps: [], note: "btc" }];
    const eth = emptyDraft(); eth.long = [{ id: "eth-1", side: "long", level: 1, offsetPct: 10, qty: 1, filledQty: 0, avgFill: null, tps: [], note: "eth" }];
    btc.enabledLong = true; btc.enabledShort = true;
    eth.enabledLong = true; eth.enabledShort = false;
    saveDraft("BTCUSDT", btc); saveDraft("ETHUSDT", eth); setSelectedSymbol("ETHUSDT");
    expect(loadWorkspace().selectedSymbol).toBe("ETHUSDT");
    expect(loadDraft("BTCUSDT")?.long[0].qty).toBe(0.1);
    expect(loadDraft("ETHUSDT")?.long[0].qty).toBe(1);
    expect(loadDraft("BTCUSDT")?.enabledShort).toBe(true);
    expect(loadDraft("ETHUSDT")?.enabledShort).toBe(false);
    const stored = JSON.parse(window.localStorage.getItem(WORKSPACE_STORAGE_KEY) ?? "{}");
    expect(stored.version).toBe(1);
    expect(JSON.stringify(stored)).not.toContain("markPrice");
    expect(JSON.stringify(stored)).not.toContain("availableMargin");
    expect(JSON.stringify(stored)).not.toContain("secret");
  });

  it("keeps factual and authoritative fields outside the draft schema", () => {
    const draft = emptyDraft() as Record<string, unknown>;
    draft.markPrice = 80360.04;
    draft.availableMargin = 81.27;
    draft.authoritative = { validation_state: "VALID" };
    saveDraft("BTCUSDT", draft as ReturnType<typeof emptyDraft>);
    const stored = JSON.parse(window.localStorage.getItem(WORKSPACE_STORAGE_KEY) ?? "{}");
    expect(stored.drafts.BTCUSDT.markPrice).toBeUndefined();
    expect(stored.drafts.BTCUSDT.availableMargin).toBeUndefined();
    expect(stored.drafts.BTCUSDT.authoritative).toBeUndefined();
  });

  it("persists generated source metadata in the local draft", () => {
    const draft = emptyDraft();
    draft.long = [{ id: "generated-1", side: "long", level: 1, offsetPct: 10, qty: 2, filledQty: 1, avgFill: 80, tps: [{ movePct: 10, closePct: 50 }], note: "", source: "GENERATED_ALGORITHM", calculatedEntryPrice: 90, manualOverrideMetadata: { source: "ALGORITHM" } }];
    saveDraft("BTCUSDT", draft);
    expect(loadDraft("BTCUSDT")?.long[0]).toMatchObject({ source: "GENERATED_ALGORITHM", calculatedEntryPrice: 90, manualOverrideMetadata: { source: "ALGORITHM" } });
  });

  it("falls back safely for corrupted and unknown versions", () => {
    window.localStorage.setItem(WORKSPACE_STORAGE_KEY, "not-json");
    expect(loadWorkspace().selectedSymbol).toBe("BTCUSDT");
    window.localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify({ version: 999, selectedSymbol: "ETHUSDT", drafts: {} }));
    expect(loadWorkspace().selectedSymbol).toBe("BTCUSDT");
  });

  it("migrates legacy generated allocation and martingale fields without using them as canonical state", () => {
    const legacy = emptyDraft() as Record<string, unknown>;
    legacy.generatedLong = { ...legacy.generatedLong as object, martingaleCoefficient: 1.5, allocationPct: 99, unrealizedReinvestPct: 12 };
    const workspace = { version: 1, selectedSymbol: "BTCUSDT", drafts: { BTCUSDT: legacy } };
    window.localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(workspace));
    const loaded = loadDraft("BTCUSDT");
    expect(loaded?.generatedLong.martingaleMultiplier).toBe(1.5);
    expect(loaded?.generatedLong.longUnrealizedReinvestPct).toBe(12);
    expect(loaded?.generatedLong).not.toHaveProperty("allocationPct");
  });

  it("removes only the requested symbol draft", () => {
    saveDraft("BTCUSDT", emptyDraft()); saveDraft("ETHUSDT", emptyDraft());
    removeDraft("BTCUSDT");
    expect(loadDraft("BTCUSDT")).toBeNull();
    expect(loadDraft("ETHUSDT")).not.toBeNull();
  });

  it("returns verified write results and exposes only safe origin diagnostics", () => {
    expect(saveDraft("XRPUSDT", emptyDraft()).ok).toBe(true);
    expect(setSelectedSymbol("XRPUSDT").ok).toBe(true);
    expect(storageDiagnostic()).toMatchObject({ key: WORKSPACE_STORAGE_KEY, selectedSymbol: "XRPUSDT", draftSymbols: ["XRPUSDT"] });
    expect(storageDiagnostic()).not.toHaveProperty("secret");
  });

  it("reports localStorage write failure without throwing", () => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = () => { throw new DOMException("quota", "QuotaExceededError"); };
    try {
      expect(saveDraft("BTCUSDT", emptyDraft())).toEqual({ ok: false, reason: "QuotaExceededError" });
    } finally {
      Storage.prototype.setItem = original;
    }
  });
});
