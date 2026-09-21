import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, History, LockKeyhole, Save, Settings2, Wifi } from "lucide-react";
import { AccountState, Allocation, GridOrder, Side, allocationLimits, guard, initialAccount, newOrder } from "./domain";
import { ApiError, fetchJson } from "./api";
import { normalizeAccountResponse } from "./accountMapping";
import { AccountApiResponse, AuditEvent, BybitDiagnosticsResponse, BybitStatusBase, CalculationResult, HealthResponse, HistoryItem, RevisionResponse, SymbolsResponse } from "./types";
import { historyItems } from "./revisionHistory";
import { money } from "./format";
import { AccountBar } from "./components/AccountBar";
import { AllocationPanel } from "./components/AllocationPanel";
import { CenterPanel } from "./components/CenterPanel";
import { GridColumn } from "./components/GridColumn";
import { HistoryDrawer } from "./components/HistoryDrawer";
import { SaveRevisionModal } from "./components/SaveRevisionModal";
import { connectionStatus, StateView } from "./components/StateView";
import { MobileAccountSnapshot } from "./components/MobileAccountSnapshot";
import { MobileBottomBar } from "./components/MobileBottomBar";
import { MobileHeader } from "./components/MobileHeader";
import { MobileSideSwitch } from "./components/MobileSideSwitch";
import { StrategySides } from "./components/StrategySides";
import { GeneratedGridPanel as GeneratedGridPanelView } from "./components/GeneratedGridPanel";
import { GeneratedSideConfig } from "./shadowTypes";
import { emptyDraft, loadDraft, loadWorkspace, removeDraft, saveDraft, setSelectedSymbol, storageDiagnostic, StoredDraft, StoredWorkspace } from "./workspaceStorage";
import "./styles.css";
import "./state.css";
import "./mobile.css";

export function App() {
  const [restoredWorkspace] = useState<StoredWorkspace>(() => loadWorkspace());
  const initialSymbol = restoredWorkspace.selectedSymbol || initialAccount.symbol;
  const initialDraft = restoredWorkspace.drafts[initialSymbol] ?? emptyDraft();
  const [account, setAccount] = useState<AccountState>(() => ({ ...initialAccount, symbol: initialSymbol }));
  const [symbols, setSymbols] = useState<string[]>([]);
  const [allocation, setAllocation] = useState<Allocation>(initialDraft.allocation);
  const [long, setLong] = useState<GridOrder[]>(initialDraft.long);
  const [short, setShort] = useState<GridOrder[]>(initialDraft.short);
  const [activeLong, setActiveLong] = useState(initialDraft.activeLong);
  const [activeShort, setActiveShort] = useState(initialDraft.activeShort);
  const [enabledLong, setEnabledLong] = useState(initialDraft.enabledLong);
  const [enabledShort, setEnabledShort] = useState(initialDraft.enabledShort);
  const [generatedLong, setGeneratedLong] = useState<GeneratedSideConfig>(initialDraft.generatedLong);
  const [generatedShort, setGeneratedShort] = useState<GeneratedSideConfig>(initialDraft.generatedShort);
  const [revisions, setRevisions] = useState<HistoryItem[]>([]);
  const [notice, setNotice] = useState("");
  const [diagnostic, setDiagnostic] = useState<BybitStatusBase | null>(null);
  const [backendConnected, setBackendConnected] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [page, setPage] = useState<"constructor" | "state">(initialDraft.page ?? "constructor");
  const [planningLeverage, setPlanningLeverage] = useState<number | null>(initialDraft.planningLeverage);
  const [authoritative, setAuthoritative] = useState<CalculationResult | null>(null);
  const [mobileSide, setMobileSide] = useState<Side>(initialDraft.mobileSide);
  const [localSavedAt, setLocalSavedAt] = useState<string | null>(initialDraft.updatedAt === new Date(0).toISOString() ? null : initialDraft.updatedAt);
  const [localSaveFailed, setLocalSaveFailed] = useState(false);
  const limitsBySide = allocationLimits(account, allocation);
  const tickSize = account.instrument?.tickSize ?? null;
  const longGuard = guard(account, allocation, "long", long, tickSize, planningLeverage);
  const shortGuard = guard(account, allocation, "short", short, tickSize, planningLeverage);

  const updateAllocation = (key: keyof Allocation, value: string) => setAllocation((current) => ({ ...current, [key]: value === "" ? null : Number(value) }));
  const editOrder = (side: Side, id: string, patch: Partial<GridOrder>) => (side === "long" ? setLong : setShort)((items) => items.map((order) => order.id === id ? { ...order, ...patch } : order));
  const addOrder = (side: Side) => { (side === "long" ? setLong : setShort)((items) => [...items, newOrder(side, items.length + 1)]); if (side === "long" && activeLong === 0) setActiveLong(1); if (side === "short" && activeShort === 0) setActiveShort(1); };
  const removeOrder = (side: Side, id: string) => (side === "long" ? setLong : setShort)((items) => items.filter((order) => order.id !== id).map((order, index) => ({ ...order, level: index + 1 })));
  const applyGenerated = (side: Side, orders: GridOrder[], active: number) => {
    const current = side === "long" ? long : short;
    if (current.length > 0 && !window.confirm(`Текущая ${side === "long" ? "Long" : "Short"} Grid будет заменена generated configuration.`)) return;
    (side === "long" ? setLong : setShort)(orders);
    (side === "long" ? setActiveLong : setActiveShort)(Math.min(Math.max(1, active), orders.length));
    setRevisions((items) => [{ time: new Date().toISOString(), action: "generated_grid_applied", side, entityType: "grid_order", entityId: `generated-${side}-${Date.now()}`, before: current, after: orders, comment: "GENERATED_ALGORITHM" }, ...items]);
    void fetchJson("/api/audit/generated-grid", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbol: account.symbol, side, source: "GENERATED_ALGORITHM", event_id: `generated-${side}-${Date.now()}`, before: { orders: current }, after: { orders, active } }) }).catch(() => undefined);
    setNotice(`${side === "long" ? "Long" : "Short"} Grid заменена generated configuration`);
  };
  const applyGeneratedBoth = (nextLong: GridOrder[], nextLongActive: number, nextShort: GridOrder[], nextShortActive: number) => {
    if ((long.length > 0 || short.length > 0) && !window.confirm("Текущие Long Grid и Short Grid будут заменены generated configuration.")) return;
    setLong(nextLong); setShort(nextShort);
    setActiveLong(Math.min(Math.max(1, nextLongActive), nextLong.length)); setActiveShort(Math.min(Math.max(1, nextShortActive), nextShort.length));
    setRevisions((items) => [{ time: new Date().toISOString(), action: "generated_grid_applied", side: "long+short", entityType: "grid_order", entityId: `generated-both-${Date.now()}`, before: { long, short }, after: { long: nextLong, short: nextShort }, comment: "GENERATED_ALGORITHM" }, ...items]);
    void fetchJson("/api/audit/generated-grid", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbol: account.symbol, side: "long+short", source: "GENERATED_ALGORITHM", event_id: `generated-both-${Date.now()}`, before: { long, short, activeLong, activeShort }, after: { long: nextLong, short: nextShort, activeLong: nextLongActive, activeShort: nextShortActive } }) }).catch(() => undefined);
    setNotice("Long Grid и Short Grid заменены generated configuration");
  };
  const GeneratedGridPanel = (_props: Record<string, unknown>) => <GeneratedGridPanelView account={account} allocation={allocation} long={generatedLong} short={generatedShort} currentLong={long} currentShort={short} currentActiveLong={activeLong} currentActiveShort={activeShort} onLongChange={setGeneratedLong} onShortChange={setGeneratedShort} onApply={applyGenerated} onApplyBoth={applyGeneratedBoth}/>;
  const draftSnapshot = (updatedAt = new Date().toISOString()): StoredDraft => ({ allocation, long, short, activeLong, activeShort, enabledLong, enabledShort, generatedLong, generatedShort, planningLeverage, mobileSide, page, updatedAt });
  const saveCurrentDraft = (symbol = account.symbol) => { const updatedAt = new Date().toISOString(); const result = saveDraft(symbol, draftSnapshot(updatedAt)); if (result.ok) { setLocalSavedAt(updatedAt); setLocalSaveFailed(false); } else { setLocalSavedAt(null); setLocalSaveFailed(true); setNotice("Не удалось сохранить локальный черновик"); } return result; };
  const restoreDraft = (stored: StoredDraft | null) => { const next = stored ?? emptyDraft(); setAllocation(next.allocation); setLong(next.long); setShort(next.short); setActiveLong(next.activeLong); setActiveShort(next.activeShort); setEnabledLong(next.enabledLong); setEnabledShort(next.enabledShort); setGeneratedLong(next.generatedLong); setGeneratedShort(next.generatedShort); setPlanningLeverage(next.planningLeverage); setMobileSide(next.mobileSide); setPage(next.page ?? "constructor"); setLocalSavedAt(stored ? next.updatedAt : null); };
  const changeSymbol = (value: string) => {
    const nextSymbol = value.toUpperCase();
    if (nextSymbol === account.symbol) return;
    saveCurrentDraft(account.symbol);
    const selectedResult = setSelectedSymbol(nextSymbol);
    if (!selectedResult.ok) { setLocalSavedAt(null); setLocalSaveFailed(true); setNotice("Не удалось сохранить локальный черновик"); }
    const nextDraft = loadDraft(nextSymbol);
    restoreDraft(nextDraft);
    setAuthoritative(null);
    setAccount({ ...initialAccount, symbol: nextSymbol, source: "ожидание обновления", stale: true });
  };
  const resetCurrentDraft = () => {
    if (typeof window !== "undefined" && !window.confirm(`Сбросить локальный черновик ${account.symbol}?`)) return;
    const result = removeDraft(account.symbol);
    if (!result.ok) { setLocalSavedAt(null); setLocalSaveFailed(true); setNotice("Не удалось сохранить локальный черновик"); return; }
    restoreDraft(null);
    setAuthoritative(null);
    setLocalSaveFailed(false);
    setNotice(`Локальный черновик ${account.symbol} сброшен`);
  };
  const toggleSide = (side: Side) => {
    const nextLong = side === "long" ? !enabledLong : enabledLong;
    const nextShort = side === "short" ? !enabledShort : enabledShort;
    if (nextLong && nextShort && account.positionMode !== "HEDGE") {
      setNotice(account.positionMode === "ONE_WAY" ? `Для одновременной Long + Short торговли по ${account.symbol} на Bybit требуется Hedge Mode.` : "Не удалось подтвердить Position Mode. Двухсторонняя конфигурация недоступна, пока режим Bybit не подтверждён.");
      return;
    }
    if (!nextLong && !nextShort) { setNotice("Включите хотя бы одну сторону стратегии"); return; }
    setEnabledLong(nextLong); setEnabledShort(nextShort);
    if (nextLong && activeLong === 0) setActiveLong(1);
    if (nextShort && activeShort === 0) setActiveShort(1);
    setNotice("");
  };
  const save = async (comment?: string) => {
    if (!authoritative) { setNotice("Сначала получите подтверждённый backend-расчёт"); return; }
    if (comment === undefined) { setSaveDialogOpen(true); return; }
    setSaving(true); setNotice("");
    try {
      const revision = await fetchJson<RevisionResponse>("/api/revisions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbol: account.symbol, comment, configuration: { symbol: account.symbol, allocation, planningLeverage, enabledLong, enabledShort, activeLongCount: enabledLong ? activeLong : 0, activeShortCount: enabledShort ? activeShort : 0, long: enabledLong ? long : [], short: enabledShort ? short : [] }, calculation: authoritative }) });
      setRevisions((items) => [{ time: revision.created_at, action: "revision_saved", entityType: "grid_revision", entityId: revision.id, comment: revision.comment }, ...items]);
      setNotice(authoritative.validation_state === "BLOCKED" ? "Версия сохранена, но конфигурация заблокирована для исполнения" : "Версия сохранена в PostgreSQL");
      setSaveDialogOpen(false);
    } catch (error) { setNotice(error instanceof ApiError ? error.message : "Не удалось сохранить: проверьте backend и PostgreSQL"); }
    setSaving(false);
  };

  const allocationComplete = allocation.longPct != null && allocation.shortPct != null && allocation.reservePct != null;
  const ordersComplete = [...long, ...short].every((order) => order.offsetPct != null && order.qty != null && order.tps.every((tp) => tp.movePct != null && tp.closePct != null));
  const planBlocked = authoritative ? authoritative.validation_state !== "VALID" : true;

  useEffect(() => {
    const load = async () => {
      try {
        const health = await fetchJson<HealthResponse>("/api/health");
        setBackendConnected(true);
        const status = health.private_state_ready ? health : await fetchJson<BybitDiagnosticsResponse>(`/api/diagnostics/bybit?symbol=${account.symbol}`);
        setDiagnostic(status);
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "Backend недоступен";
        setBackendConnected(false);
        setDiagnostic({ environment: "mainnet", credential_source: "none", account_state_ready: false, orders_ready: false, private_state_ready: false, last_safe_error: message });
        setAccount((current) => ({ ...current, stale: true, error: message }));
        return;
      }
      try { const data = await fetchJson<AccountApiResponse>(`/api/state/${account.symbol}`); setAccount((current) => normalizeAccountResponse(data, current)); }
      catch (error) { const message = error instanceof ApiError ? error.message : "Нет свежего обновления Bybit"; setAccount((current) => ({ ...current, stale: true, error: message })); }
    };
    void load();
    const timer = setInterval(() => void load(), 15000);
    return () => clearInterval(timer);
  }, [account.symbol]);

  useEffect(() => { void fetchJson<SymbolsResponse>("/api/symbols").then((data) => setSymbols(data.symbols || [])).catch(() => setSymbols([])); if (import.meta.env.DEV) console.info("Manual Grid local storage", storageDiagnostic()); }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => { const updatedAt = new Date().toISOString(); const result = saveDraft(account.symbol, draftSnapshot(updatedAt)); if (result.ok) { setLocalSavedAt(updatedAt); setLocalSaveFailed(false); } else { setLocalSavedAt(null); setLocalSaveFailed(true); setNotice("Не удалось сохранить локальный черновик"); } }, 400);
    return () => window.clearTimeout(timer);
  }, [account.symbol, allocation, long, short, activeLong, activeShort, enabledLong, enabledShort, generatedLong, generatedShort, planningLeverage, mobileSide, page]);
  useEffect(() => {
    const saveBeforeUnload = () => { const result = saveDraft(account.symbol, draftSnapshot()); if (!result.ok) { setLocalSavedAt(null); setLocalSaveFailed(true); setNotice("Не удалось сохранить локальный черновик"); } };
    window.addEventListener("pagehide", saveBeforeUnload);
    return () => window.removeEventListener("pagehide", saveBeforeUnload);
  }, [account.symbol, allocation, long, short, activeLong, activeShort, enabledLong, enabledShort, generatedLong, generatedShort, planningLeverage, mobileSide, page]);
  useEffect(() => {
    if (!historyOpen) return;
    void Promise.all([fetchJson<AuditEvent[]>("/api/audit"), fetchJson<RevisionResponse[]>(`/api/revisions?symbol=${encodeURIComponent(account.symbol)}`)]).then(([events, saved]) => setRevisions(historyItems(events, saved))).catch(() => undefined);
  }, [historyOpen, account.symbol]);
  useEffect(() => {
    const enabledOrdersComplete = (!enabledLong || (long.length > 0 && activeLong >= 1)) && (!enabledShort || (short.length > 0 && activeShort >= 1));
    const enabledFieldsComplete = (!enabledLong || long.every((order) => order.offsetPct != null && order.qty != null && order.tps.every((tp) => tp.movePct != null && tp.closePct != null))) && (!enabledShort || short.every((order) => order.offsetPct != null && order.qty != null && order.tps.every((tp) => tp.movePct != null && tp.closePct != null)));
    if (!allocationComplete || !enabledOrdersComplete || !enabledFieldsComplete || (!enabledLong && !enabledShort) || (enabledLong && enabledShort && account.positionMode !== "HEDGE") || account.markPrice == null || account.availableMargin == null || !account.instrument || [account.instrument.tickSize, account.instrument.qtyStep, account.instrument.minOrderQty, account.instrument.minNotionalValue].some((value) => value == null) || planningLeverage == null) { setAuthoritative(null); return; }
    const payload = { symbol: account.symbol, planningLeverage, allocation, enabledLong, enabledShort, activeLongCount: enabledLong ? activeLong : 0, activeShortCount: enabledShort ? activeShort : 0, long, short };
    const timer = setTimeout(async () => { try { setAuthoritative(await fetchJson<CalculationResult>("/api/calculate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })); } catch { setAuthoritative(null); } }, 250);
    return () => clearTimeout(timer);
  }, [account, allocation, activeLong, activeShort, enabledLong, enabledShort, long, short, planningLeverage]);

  const statusText = account.error ? "Backend доступен, Bybit private data недоступны" : connectionStatus(Boolean(diagnostic?.account_state_ready), Boolean(diagnostic?.orders_ready), backendConnected);
  const selectedOrders = mobileSide === "long" ? long : short;
  const selectedCalculation = mobileSide === "long" ? authoritative?.long : authoritative?.short;
  const selectedActive = Math.max(1, mobileSide === "long" ? activeLong : activeShort);
  const selectedLimit = selectedCalculation ? Number(selectedCalculation.allocation_limit) : null;
  const selectedPlanned = selectedCalculation ? Number(selectedCalculation.full_grid_planned_margin) : null;
  return <div className="app-shell"><aside className="sidebar"><div className="logo"><span>G</span><div>СЕТКА<br/><b>КОНТРОЛЬ</b></div></div><div className="mode-pill"><span></span> {diagnostic?.environment === "testnet" ? "BYBIT TESTNET · ТОЛЬКО ЧТЕНИЕ" : diagnostic?.environment === "mainnet" ? "BYBIT MAINNET · ТОЛЬКО ЧТЕНИЕ" : "ОЖИДАНИЕ ПОДКЛЮЧЕНИЯ"}</div><nav><button className={page === "constructor" ? "active" : ""} onClick={() => setPage("constructor")}><Settings2 size={16}/> Конструктор</button><button className={page === "state" ? "active" : ""} onClick={() => setPage("state")}><Activity size={16}/> Факты аккаунта</button><button onClick={() => setHistoryOpen(true)}><History size={16}/> История</button></nav><div className="sidebar-bottom"><LockKeyhole size={15}/><span>Только чтение<br/><small>Торговые команды отключены</small></span></div></aside><main className="content"><MobileHeader account={account} symbols={symbols} onSymbol={changeSymbol} environment={diagnostic?.environment ?? null} connected={backendConnected}/><header className="topbar"><div><div className="crumb">РУЧНАЯ СЕТКА / НАСТРОЙКА</div><h1>Ручная настройка сетки</h1>{notice && <div className="notice">{notice}</div>}</div><div className="top-actions"><span className="connection"><Wifi size={14}/> {statusText}{backendConnected && diagnostic?.account_state_ready && !diagnostic.orders_ready ? " · Открытые ордера временно недоступны" : ""}</span><div className="draft-status">Локальный черновик · {localSavedAt ? `сохранено ${new Date(localSavedAt).toLocaleTimeString("ru-RU")}` : "изменения сохраняются автоматически"}<button className="draft-reset" onClick={resetCurrentDraft}>Сбросить</button></div><button className="outline" onClick={() => setHistoryOpen(true)}><History size={16}/> История</button><button className="save" onClick={() => void save()}><Save size={16}/> {saving ? "Сохраняю…" : "Сохранить версию"}</button></div></header><MobileAccountSnapshot account={account} draftSavedAt={localSavedAt} onReset={resetCurrentDraft}/><AccountBar account={account} symbols={symbols} leverage={planningLeverage} onSymbol={changeSymbol} onLeverage={setPlanningLeverage}/>{page === "constructor" ? <><AllocationPanel account={account} allocation={allocation} limits={limitsBySide} onChange={updateAllocation} enabledLong={enabledLong} enabledShort={enabledShort} onToggleSide={toggleSide}/><GeneratedGridPanel account={account} allocation={allocation} long={generatedLong} short={generatedShort} onLongChange={setGeneratedLong} onShortChange={setGeneratedShort}/><MobileSideSwitch selected={mobileSide} onChange={setMobileSide}/><div className="mobile-side-summary"><div><b>{mobileSide === "long" ? "ЛОНГ-СЕТКА" : "ШОРТ-СЕТКА"}</b><span>{selectedOrders.length} уровней · Активное окно: {selectedActive}</span></div><strong>{selectedPlanned == null ? "—" : money(selectedPlanned)}<small>{selectedLimit == null ? "Заполните параметры" : `из ${money(selectedLimit)}`}</small></strong></div><div className={`three-columns mobile-side-${mobileSide}`}><GridColumn side="long" orders={long} active={activeLong} mark={account.markPrice} tickSize={tickSize} leverage={planningLeverage} guard={longGuard} calculation={authoritative?.long} onActive={setActiveLong} onAdd={() => addOrder("long")} onEdit={(id, patch) => editOrder("long", id, patch)} onRemove={(id) => removeOrder("long", id)}/><CenterPanel account={account} long={long} short={short} tickSize={tickSize} calculation={authoritative} blocked={planBlocked}/><GridColumn side="short" orders={short} active={activeShort} mark={account.markPrice} tickSize={tickSize} leverage={planningLeverage} guard={shortGuard} calculation={authoritative?.short} onActive={setActiveShort} onAdd={() => addOrder("short")} onEdit={(id, patch) => editOrder("short", id, patch)} onRemove={(id) => removeOrder("short", id)}/></div></> : <StateView account={account}/>}</main><MobileBottomBar statePage={page === "state"} onConstructor={() => setPage("constructor")} onState={() => setPage("state")} onHistory={() => setHistoryOpen(true)} onSave={() => void save()} saving={saving}/>{historyOpen && <HistoryDrawer items={revisions} close={() => setHistoryOpen(false)}/>} {saveDialogOpen && <SaveRevisionModal saving={saving} close={() => setSaveDialogOpen(false)} save={(comment) => void save(comment)}/>}</div>;
}

if (document.getElementById("root")) createRoot(document.getElementById("root")!).render(<App/>);
