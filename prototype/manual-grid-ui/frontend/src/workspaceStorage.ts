import { Allocation, GridOrder, Side, TP } from "./domain";
import { GeneratedSideConfig, defaultGeneratedSide } from "./shadowTypes";

export const WORKSPACE_STORAGE_KEY = "manual-grid-workspace:v1";
export const WORKSPACE_VERSION = 1 as const;
export const DEFAULT_SYMBOL = "BTCUSDT";

export type StoredDraft = {
  allocation: Allocation;
  long: GridOrder[];
  short: GridOrder[];
  activeLong: number;
  activeShort: number;
  enabledLong: boolean;
  enabledShort: boolean;
  generatedLong: GeneratedSideConfig;
  generatedShort: GeneratedSideConfig;
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

export type StorageWriteResult = { ok: true } | { ok: false; reason: string };

export type StorageDiagnostic = {
  origin: string;
  key: string;
  selectedSymbol: string;
  draftSymbols: string[];
};

export function emptyDraft(): StoredDraft {
  return { allocation: { longPct: null, shortPct: null, reservePct: null }, long: [], short: [], activeLong: 0, activeShort: 0, enabledLong: true, enabledShort: true, generatedLong: defaultGeneratedSide(true, 30), generatedShort: defaultGeneratedSide(false, 20), planningLeverage: null, mobileSide: "long", page: "constructor", updatedAt: new Date(0).toISOString() };
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
  if (!item || !itemAllocation || !Array.isArray(item.long) || !Array.isArray(item.short) || typeof item.activeLong !== "number" || typeof item.activeShort !== "number" || !Number.isFinite(item.activeLong) || !Number.isFinite(item.activeShort) || (item.enabledLong !== undefined && typeof item.enabledLong !== "boolean") || (item.enabledShort !== undefined && typeof item.enabledShort !== "boolean") || !(item.planningLeverage === null || (typeof item.planningLeverage === "number" && Number.isFinite(item.planningLeverage))) || (item.mobileSide !== "long" && item.mobileSide !== "short") || (item.page !== undefined && item.page !== "constructor" && item.page !== "state") || typeof item.updatedAt !== "string") return null;
  const long = item.long.map(order); const short = item.short.map(order);
  if (long.some((value) => value === null) || short.some((value) => value === null)) return null;
  const generatedLong = record(item.generatedLong);
  const generatedShort = record(item.generatedShort);
  const generated = (value: Record<string, unknown> | null, fallback: GeneratedSideConfig): GeneratedSideConfig => value && typeof value.orderCount === "number" && typeof value.gridDepthPct === "number" && typeof value.firstOrderOffsetPct === "number" && typeof value.distributionCoefficient === "number" && typeof value.leverage === "number" && typeof value.martingaleCoefficient === "number" && typeof value.allocationPct === "number" && typeof value.activeOrderCount === "number" && Array.isArray(value.tpSteps) ? { ...fallback, ...(value as Partial<GeneratedSideConfig>) } : fallback;
  return { allocation: itemAllocation, long: long as GridOrder[], short: short as GridOrder[], activeLong: item.activeLong, activeShort: item.activeShort, enabledLong: item.enabledLong ?? true, enabledShort: item.enabledShort ?? true, generatedLong: generated(generatedLong, defaultGeneratedSide(true, 30)), generatedShort: generated(generatedShort, defaultGeneratedSide(false, 20)), planningLeverage: item.planningLeverage, mobileSide: item.mobileSide, page: item.page, updatedAt: item.updatedAt };
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

export function saveWorkspace(workspace: StoredWorkspace): StorageWriteResult {
  const target = storage();
  if (!target) return { ok: false, reason: "localStorage недоступен" };
  try {
    target.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify({ ...workspace, version: WORKSPACE_VERSION }));
    const verified = loadWorkspace();
    if (verified.version !== WORKSPACE_VERSION || verified.selectedSymbol !== workspace.selectedSymbol) return { ok: false, reason: "проверка localStorage не пройдена" };
    return { ok: true };
  } catch (error) {
    const name = error && typeof error === "object" && "name" in error && typeof error.name === "string" ? error.name : null;
    return { ok: false, reason: name || "ошибка записи localStorage" };
  }
}

export function loadDraft(symbol: string): StoredDraft | null { return loadWorkspace().drafts[symbol.toUpperCase()] ?? null; }

export function saveDraft(symbol: string, value: StoredDraft): StorageWriteResult {
  const workspace = loadWorkspace();
  const normalizedSymbol = symbol.toUpperCase();
  workspace.drafts[normalizedSymbol] = { allocation: value.allocation, long: value.long, short: value.short, activeLong: value.activeLong, activeShort: value.activeShort, enabledLong: value.enabledLong, enabledShort: value.enabledShort, generatedLong: value.generatedLong, generatedShort: value.generatedShort, planningLeverage: value.planningLeverage, mobileSide: value.mobileSide, page: value.page, updatedAt: value.updatedAt };
  const result = saveWorkspace(workspace);
  if (!result.ok) return result;
  return loadDraft(normalizedSymbol) ? result : { ok: false, reason: "черновик не найден после записи" };
}

export function removeDraft(symbol: string): StorageWriteResult {
  const workspace = loadWorkspace();
  delete workspace.drafts[symbol.toUpperCase()];
  const result = saveWorkspace(workspace);
  if (!result.ok) return result;
  return loadDraft(symbol) === null ? result : { ok: false, reason: "черновик не удалён после записи" };
}

export function setSelectedSymbol(symbol: string): StorageWriteResult {
  const workspace = loadWorkspace();
  const expected = symbol.toUpperCase();
  workspace.selectedSymbol = expected;
  const result = saveWorkspace(workspace);
  if (!result.ok) return result;
  return loadWorkspace().selectedSymbol === expected ? result : { ok: false, reason: "выбранный символ не подтверждён после записи" };
}

export function storageDiagnostic(): StorageDiagnostic {
  const workspace = loadWorkspace();
  return { origin: typeof window === "undefined" ? "server" : window.location.origin, key: WORKSPACE_STORAGE_KEY, selectedSymbol: workspace.selectedSymbol, draftSymbols: Object.keys(workspace.drafts) };
}
