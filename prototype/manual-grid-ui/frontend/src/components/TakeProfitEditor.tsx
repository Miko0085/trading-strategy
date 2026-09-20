import { Plus, Trash2 } from "lucide-react";
import { GridOrder, TP, tpPrice, pnl } from "../domain";
import { TPCalculationResult } from "../types";
import { money, pct, price, qty } from "../format";

export function tpDisplayModel(order: GridOrder, entryPrice: number | null, tp: TP, tickSize: number | null, backend?: TPCalculationResult) {
  const authoritative = Boolean(backend);
  return { authoritative, badge: authoritative ? "Backend" : "Preview", price: authoritative ? Number(backend?.price) : tpPrice(order, entryPrice, tp, tickSize), grossPnl: authoritative ? Number(backend?.gross_pnl) : pnl(order, entryPrice, tp, tickSize), fee: authoritative ? backend?.fee ?? null : null, netPnl: authoritative ? backend?.net_pnl ?? null : null };
}

export function TakeProfitEditor({ order, entryPrice, tickSize, backendTps, onChange }: { order: GridOrder; entryPrice: number | null; tickSize: number | null; backendTps: TPCalculationResult[]; onChange: (patch: Partial<GridOrder>) => void }) {
  const total = order.tps.reduce((sum, tp) => sum + (tp.closePct ?? 0), 0);
  const update = (index: number, patch: Partial<TP>) => { const tps = order.tps.map((tp, i) => i === index ? { ...tp, ...patch } : tp); onChange({ tps }); };
  return <div className="tp-section"><div className="tp-title"><b>Тейк-профит</b><span className={total > 100 ? "danger" : ""}>{pct(total)} закрытия · осталось {pct(Math.max(0, 100 - total))}</span><button onClick={() => onChange({ tps: [...order.tps, { movePct: null, closePct: null }] })}><Plus size={13}/> Добавить</button></div>{order.tps.map((tp, index) => { const model = tpDisplayModel(order, entryPrice, tp, tickSize, backendTps[index]); const backend = backendTps[index]; return <div className="tp-line" key={index}><span>TP {index + 1}</span><input inputMode="decimal" type="number" value={tp.movePct ?? ""} onChange={(event) => update(index, { movePct: event.target.value === "" ? null : Number(event.target.value) })}/><span>% →</span><input inputMode="decimal" type="number" value={tp.closePct ?? ""} onChange={(event) => update(index, { closePct: event.target.value === "" ? null : Number(event.target.value) })}/><span>% объёма</span><b>{price(model.price)}</b><em>{money(model.grossPnl)}</em><small><span className="calc-badge">{model.badge}</span> · {model.authoritative ? `TP qty: ${qty(Number(backend?.qty))} · ${model.fee == null ? "Комиссия не задана" : `fee ${money(Number(model.fee))}`} · ${model.netPnl == null ? "net P&L: нет данных" : `net ${money(Number(model.netPnl))}`}` : "Комиссия не задана · net P&L: нет данных"}</small><button className="delete" aria-label={`Удалить TP ${index + 1}`} onClick={() => onChange({ tps: order.tps.filter((_, i) => i !== index) })}><Trash2 size={12}/></button></div>; })}</div>;
}
