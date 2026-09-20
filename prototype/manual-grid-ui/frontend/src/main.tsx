import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, History, LockKeyhole, Save, Settings2, Wifi } from "lucide-react";
import { AccountState, Allocation, GridOrder, Side, allocationLimits, guard, initialAccount, newOrder } from "./domain";
import { ApiError, fetchJson } from "./api";
import { normalizeAccountResponse } from "./accountMapping";
import { AccountApiResponse, AuditEvent, BybitDiagnosticsResponse, BybitStatusBase, CalculationResult, HealthResponse, HistoryItem, RevisionResponse, SymbolsResponse } from "./types";
import { historyItems } from "./revisionHistory";
import { AccountBar } from "./components/AccountBar";
import { AllocationPanel } from "./components/AllocationPanel";
import { CenterPanel } from "./components/CenterPanel";
import { GridColumn } from "./components/GridColumn";
import { HistoryDrawer } from "./components/HistoryDrawer";
import { SaveRevisionModal } from "./components/SaveRevisionModal";
import { connectionStatus, StateView } from "./components/StateView";
import "./styles.css";
import "./state.css";

function App() {
  const [account, setAccount] = useState<AccountState>(initialAccount);
  const [symbols, setSymbols] = useState<string[]>([]);
  const [allocation, setAllocation] = useState<Allocation>({ longPct: null, shortPct: null, reservePct: null });
  const [long, setLong] = useState<GridOrder[]>([]);
  const [short, setShort] = useState<GridOrder[]>([]);
  const [activeLong, setActiveLong] = useState(0);
  const [activeShort, setActiveShort] = useState(0);
  const [revisions, setRevisions] = useState<HistoryItem[]>([]);
  const [notice, setNotice] = useState("");
  const [diagnostic, setDiagnostic] = useState<BybitStatusBase | null>(null);
  const [backendConnected, setBackendConnected] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [page, setPage] = useState<"constructor" | "state">("constructor");
  const [planningLeverage, setPlanningLeverage] = useState<number | null>(null);
  const [authoritative, setAuthoritative] = useState<CalculationResult | null>(null);
  const limitsBySide = allocationLimits(account, allocation);
  const tickSize = account.instrument?.tickSize ?? null;
  const longGuard = guard(account, allocation, "long", long, tickSize, planningLeverage);
  const shortGuard = guard(account, allocation, "short", short, tickSize, planningLeverage);

  const updateAllocation = (key: keyof Allocation, value: string) => setAllocation((current) => ({ ...current, [key]: value === "" ? null : Number(value) }));
  const editOrder = (side: Side, id: string, patch: Partial<GridOrder>) => (side === "long" ? setLong : setShort)((items) => items.map((order) => order.id === id ? { ...order, ...patch } : order));
  const addOrder = (side: Side) => { (side === "long" ? setLong : setShort)((items) => [...items, newOrder(side, items.length + 1)]); if (side === "long" && activeLong === 0) setActiveLong(1); if (side === "short" && activeShort === 0) setActiveShort(1); };
  const removeOrder = (side: Side, id: string) => (side === "long" ? setLong : setShort)((items) => items.filter((order) => order.id !== id).map((order, index) => ({ ...order, level: index + 1 })));
  const save = async (comment?: string) => {
    if (!authoritative) { setNotice("Сначала получите подтверждённый backend-расчёт"); return; }
    if (comment === undefined) { setSaveDialogOpen(true); return; }
    setSaving(true); setNotice("");
    try {
      const revision = await fetchJson<RevisionResponse>("/api/revisions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbol: account.symbol, comment, configuration: { symbol: account.symbol, allocation, planningLeverage, activeLongCount: activeLong, activeShortCount: activeShort, long, short }, calculation: authoritative }) });
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

  useEffect(() => { void fetchJson<SymbolsResponse>("/api/symbols").then((data) => setSymbols(data.symbols || [])).catch(() => setSymbols([])); }, []);
  useEffect(() => {
    if (!historyOpen) return;
    void Promise.all([fetchJson<AuditEvent[]>("/api/audit"), fetchJson<RevisionResponse[]>(`/api/revisions?symbol=${encodeURIComponent(account.symbol)}`)]).then(([events, saved]) => setRevisions(historyItems(events, saved))).catch(() => undefined);
  }, [historyOpen, account.symbol]);
  useEffect(() => {
    if (!allocationComplete || !ordersComplete || long.length === 0 || short.length === 0 || activeLong < 1 || activeShort < 1 || account.markPrice == null || account.availableMargin == null || !account.instrument || [account.instrument.tickSize, account.instrument.qtyStep, account.instrument.minOrderQty, account.instrument.minNotionalValue].some((value) => value == null) || planningLeverage == null) { setAuthoritative(null); return; }
    const payload = { symbol: account.symbol, planningLeverage, allocation, activeLongCount: activeLong, activeShortCount: activeShort, long, short };
    const timer = setTimeout(async () => { try { setAuthoritative(await fetchJson<CalculationResult>("/api/calculate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })); } catch { setAuthoritative(null); } }, 250);
    return () => clearTimeout(timer);
  }, [account, allocation, activeLong, activeShort, long, short, planningLeverage]);

  const statusText = account.error ? "Backend доступен, Bybit private data недоступны" : connectionStatus(Boolean(diagnostic?.account_state_ready), Boolean(diagnostic?.orders_ready), backendConnected);
  return <div className="app-shell"><aside className="sidebar"><div className="logo"><span>G</span><div>СЕТКА<br/><b>КОНТРОЛЬ</b></div></div><div className="mode-pill"><span></span> {diagnostic?.environment === "testnet" ? "BYBIT TESTNET · ТОЛЬКО ЧТЕНИЕ" : diagnostic?.environment === "mainnet" ? "BYBIT MAINNET · ТОЛЬКО ЧТЕНИЕ" : "ОЖИДАНИЕ ПОДКЛЮЧЕНИЯ"}</div><nav><button className={page === "constructor" ? "active" : ""} onClick={() => setPage("constructor")}><Settings2 size={16}/> Конструктор</button><button className={page === "state" ? "active" : ""} onClick={() => setPage("state")}><Activity size={16}/> Факты аккаунта</button><button onClick={() => setHistoryOpen(true)}><History size={16}/> История</button></nav><div className="sidebar-bottom"><LockKeyhole size={15}/><span>Только чтение<br/><small>Торговые команды отключены</small></span></div></aside><main className="content"><header className="topbar"><div><div className="crumb">РУЧНАЯ СЕТКА / НАСТРОЙКА</div><h1>Ручная настройка сетки</h1>{notice && <div className="notice">{notice}</div>}</div><div className="top-actions"><span className="connection"><Wifi size={14}/> {statusText}{backendConnected && diagnostic?.account_state_ready && !diagnostic.orders_ready ? " · Открытые ордера временно недоступны" : ""}</span><button className="outline" onClick={() => setHistoryOpen(true)}><History size={16}/> История</button><button className="save" onClick={() => void save()}><Save size={16}/> {saving ? "Сохраняю…" : "Сохранить версию"}</button></div></header><AccountBar account={account} symbols={symbols} leverage={planningLeverage} onSymbol={(symbol) => setAccount((current) => ({ ...current, symbol, stale: true, source: "ожидание обновления", updatedAt: null }))} onLeverage={setPlanningLeverage}/>{page === "constructor" ? <><AllocationPanel account={account} allocation={allocation} limits={limitsBySide} onChange={updateAllocation}/><div className="three-columns"><GridColumn side="long" orders={long} active={activeLong} mark={account.markPrice} tickSize={tickSize} leverage={planningLeverage} guard={longGuard} calculation={authoritative?.long} onActive={setActiveLong} onAdd={() => addOrder("long")} onEdit={(id, patch) => editOrder("long", id, patch)} onRemove={(id) => removeOrder("long", id)}/><CenterPanel account={account} long={long} short={short} tickSize={tickSize} calculation={authoritative} blocked={planBlocked}/><GridColumn side="short" orders={short} active={activeShort} mark={account.markPrice} tickSize={tickSize} leverage={planningLeverage} guard={shortGuard} calculation={authoritative?.short} onActive={setActiveShort} onAdd={() => addOrder("short")} onEdit={(id, patch) => editOrder("short", id, patch)} onRemove={(id) => removeOrder("short", id)}/></div></> : <StateView account={account}/>}</main>{historyOpen && <HistoryDrawer items={revisions} close={() => setHistoryOpen(false)}/>} {saveDialogOpen && <SaveRevisionModal saving={saving} close={() => setSaveDialogOpen(false)} save={(comment) => void save(comment)}/>}</div>;
}

createRoot(document.getElementById("root")!).render(<App/>);
