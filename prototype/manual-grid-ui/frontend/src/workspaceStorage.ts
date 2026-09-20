import { Allocation, GridOrder, Side, TP } from "./domain";

export const WORKSPACE_STORAGE_KEY = "manual-grid-workspace:v1";
export const WORKSPACE_VERSION = 1 as const;
export const DEFAULT_SYMBOL = "BTCUSDT";

export type StoredDraft = {
  allocation: Allocation;
  long: GridOrder[];
  short: GridOrder[];
  activeLong: number;
  activeShort: number;
  planningLeverage: number | null;
  mobileSide: Side;
  page?: "constructor" | "state";
  updatedAt: string;
};

export type StoredWorkspace = {
  version: typeof WORKSPACE_VERSION;
  selectedSymbol: string;
  drafts: Record<string, StoredDraft>;
};

export function emptyDraft(): StoredDraft {
  return { allocation: { longPct: null, shortPct: null, reservePct: null }, long: [], short: [], activeLong: 0, activeShort: 0, planningLeverage: null, mobileSide: "long", page: "constructor", updatedAt: new Date(0).toISOString() };
}

export function emptyWorkspace(): StoredWorkspace {
  return { version: WORKSPACE_VERSION, selectedSymbol: DEFAULT_SYMBOL, drafts: {} };
}

function storage(): Storage | null {
  try { return typeof window === "undefined" ? null : window.localStorage; } catch { return null; }
}

function record(value: unknown): Record<string, unknown> | null { return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null; }
function numberOrNull(value: unknown): value is number | null { return value === null || (typeof value === "number" && Number.isFinite(value)); }
function allocation(value: unknown): Allocation | null {
  const item = record(value);
  if (!item || !numberOrNull(item.longPct) || !numberOrNull(item.shortPct) || !numberOrNull(item.reservePct)) return null;
  return { longPct: item.longPct, shortPct: item.shortPct, reservePct: item.reservePct };
}
function order(value: unknown): GridOrder | null {
  const item = record(value);
  if (!item || typeof item.id !== "string" || (item.side !== "long" && item.side !== "short") || typeof item.level !== "number" || !Number.isFinite(item.level) || !numberOrNull(item.offsetPct) || !numberOrNull(item.qty) || typeof item.filledQty !== "number" || !Number.isFinite(item.filledQty) || !numberOrNull(item.avgFill) || !Array.isArray(item.tps) || typeof item.note !== "string") return null;
  const tps = item.tps.map((value) => { const tp = record(value); return tp && numberOrNull(tp.movePct) && numberOrNull(tp.closePct) ? { movePct: tp.movePct, closePct: tp.closePct } : null; });
  if (tps.some((value) => value === null)) return null;
  return { id: item.id, side: item.side, level: item.level, offsetPct: item.offsetPct, qty: item.qty, filledQty: item.filledQty, avgFill: item.avgFill, tps: tps as TP[], note: item.note };
}
function draft(value: unknown): StoredDraft | null {
  const item = record(value);
  const itemAllocation = allocation(item?.allocation);
  if (!item || !itemAllocation || !Array.isArray(item.long) || !Array.isArray(item.short) || typeof item.activeLong !== "number" || typeof item.activeShort !== "number" || !Number.isFinite(item.activeLong) || !Number.isFinite(item.activeShort) || !(item.planningLeverage === null || (typeof item.planningLeverage === "number" && Number.isFinite(item.planningLeverage))) || (item.mobileSide !== "long" && item.mobileSide !== "short") || (item.page !== undefined && item.page !== "constructor" && item.page !== "state") || typeof item.updatedAt !== "string") return null;
  const long = item.long.map(order); const short = item.short.map(order);
  if (long.some((value) => value === null) || short.some((value) => value === null)) return null;
  return { allocation: itemAllocation, long: long as GridOrder[], short: short as GridOrder[], activeLong: item.activeLong, activeShort: item.activeShort, planningLeverage: item.planningLeverage, mobileSide: item.mobileSide, page: item.page, updatedAt: item.updatedAt };
}

export function loadWorkspace(): StoredWorkspace {
  const rawStorage = storage();
  if (!rawStorage) return emptyWorkspace();
  try {
    const parsed: unknown = JSON.parse(rawStorage.getItem(WORKSPACE_STORAGE_KEY) ?? "");
    const item = record(parsed);
    if (!item || item.version !== WORKSPACE_VERSION || typeof item.selectedSymbol !== "string" || item.selectedSymbol.trim() === "" || !record(item.drafts)) return emptyWorkspace();
    const drafts: Record<string, StoredDraft> = {};
    for (const [symbol, value] of Object.entries(item.drafts as Record<string, unknown>)) { const parsedDraft = draft(value); if (parsedDraft) drafts[symbol.toUpperCase()] = parsedDraft; }
    return { version: WORKSPACE_VERSION, selectedSymbol: item.selectedSymbol.toUpperCase(), drafts };
  } catch { return emptyWorkspace(); }
}

export function saveWorkspace(workspace: StoredWorkspace): void {
  try { storage()?.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify({ ...workspace, version: WORKSPACE_VERSION })); } catch { /* Safari private mode/quota: draft remains in React state. */ }
}

export function loadDraft(symbol: string): StoredDraft | null { return loadWorkspace().drafts[symbol.toUpperCase()] ?? null; }

export function saveDraft(symbol: string, value: StoredDraft): void {
  const workspace = loadWorkspace();
  workspace.drafts[symbol.toUpperCase()] = { allocation: value.allocation, long: value.long, short: value.short, activeLong: value.activeLong, activeShort: value.activeShort, planningLeverage: value.planningLeverage, mobileSide: value.mobileSide, page: value.page, updatedAt: value.updatedAt };
  saveWorkspace(workspace);
}

export function removeDraft(symbol: string): void {
  const workspace = loadWorkspace();
  delete workspace.drafts[symbol.toUpperCase()];
  saveWorkspace(workspace);
}

export function setSelectedSymbol(symbol: string): void {
  const workspace = loadWorkspace();
  workspace.selectedSymbol = symbol.toUpperCase();
  saveWorkspace(workspace);
}
