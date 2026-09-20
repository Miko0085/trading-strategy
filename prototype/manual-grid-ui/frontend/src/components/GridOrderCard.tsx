import { Trash2 } from "lucide-react";
import { GridOrder, margin, pnl, tpPrice } from "../domain";
import { OrderCalculationResult } from "../types";
import { money, price, qty } from "../format";
import { ValidationMessages } from "./ValidationMessages";
import { TakeProfitEditor } from "./TakeProfitEditor";
import { useState } from "react";

export function orderDisplayModel(order: GridOrder, previewPrice: number | null, calculated: OrderCalculationResult | undefined, leverage: number | null) {
  const isAuthoritative = Boolean(calculated);
  return { isAuthoritative, badge: isAuthoritative ? "Backend" : "Preview", price: isAuthoritative ? Number(calculated?.planned_entry_price) : previewPrice, margin: isAuthoritative ? Number(calculated?.planned_margin ?? NaN) : margin(order, previewPrice, leverage) };
}

export function GridOrderCard({ order, price: previewPrice, calculated, tickSize, leverage, active, onEdit, onRemove }: { order: GridOrder; price: number | null; calculated?: OrderCalculationResult; tickSize: number | null; leverage: number | null; active: boolean; onEdit: (patch: Partial<GridOrder>) => void; onRemove: () => void }) {
  const [expanded, setExpanded] = useState(() => typeof window === "undefined" || !window.matchMedia?.("(max-width: 760px)").matches || order.level === 1);
  const display = orderDisplayModel(order, previewPrice, calculated, leverage);
  const { isAuthoritative, price: displayPrice, margin: displayMargin } = display;
  const configuredQty = isAuthoritative ? Number(calculated?.configured_qty) : order.qty;
  const displayNotional = isAuthoritative ? Number(calculated?.notional) : null;
  const average = isAuthoritative && calculated?.cumulative_planned_average != null ? Number(calculated.cumulative_planned_average) : null;
  const tps = calculated?.tp_steps ?? [];
  const total = order.tps.reduce((sum, tp) => sum + (tp.closePct ?? 0), 0);
  return <article className={`order-card ${active ? "active" : "queued"}`}><div className="order-top"><span className="level">#{order.level}</span><span className={`order-status ${active ? "green" : "gray"}`}>{active ? "В активном окне" : "В очереди"}</span><span className="calc-badge">{isAuthoritative ? "Backend" : "Preview"}</span><button className="collapse" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? "Свернуть" : "Развернуть"}</button><button className="delete" aria-label={`Удалить уровень ${order.level}`} onClick={onRemove}><Trash2 size={14}/></button></div><div className="price-row"><div><span>Плановая цена входа</span><b>{price(displayPrice)}</b></div><div><span>{order.level === 1 ? "Отступ от текущей цены" : "Отступ от предыдущего"}</span><label><input inputMode="decimal" type="number" value={order.offsetPct ?? ""} step="0.1" onChange={(event) => onEdit({ offsetPct: event.target.value === "" ? null : Number(event.target.value) })}/> %</label></div></div>{expanded && <div className="mobile-order-details"><div className="order-inputs"><label>Объём, монет<input inputMode="decimal" type="number" value={order.qty ?? ""} onChange={(event) => onEdit({ qty: event.target.value === "" ? null : Number(event.target.value) })}/></label><div><span>Цена / количество</span><b>{price(displayPrice)} · {qty(configuredQty)}</b></div><div><span>Notional / маржа</span><b>{money(displayNotional)} · {money(displayMargin)}</b></div><div><span>Средняя после уровня</span><b>{price(average)}</b></div><div><span>Фактическое исполнение</span><b>не связано с уровнем</b></div></div><ValidationMessages calculated={calculated}/><TakeProfitEditor order={order} entryPrice={displayPrice} tickSize={tickSize} backendTps={tps} onChange={onEdit}/><div className="order-result"><span>Запланировано TP: {qty(calculated?.planned_tp_qty == null ? null : Number(calculated.planned_tp_qty))}</span><span>Остаток после TP: {qty(calculated?.planned_remaining_after_all_tp == null ? null : Number(calculated.planned_remaining_after_all_tp))}</span><span>Основа: {calculated?.tp_steps?.[0]?.basis === "actual_fill" ? "Фактическая средняя" : "Плановая цена входа"}</span><span>{isAuthoritative ? "Источник: Backend" : "Источник: Preview"}</span></div><input className="note" placeholder="Заметка к ордеру..." value={order.note} onChange={(event) => onEdit({ note: event.target.value })}/></div>}</article>;
}
