import { Check, ShieldCheck, Wifi } from "lucide-react";
import { AccountState } from "../domain";
import { money, price, qty } from "../format";

export function stateOrdersMessage(account: AccountState): string {
  if (!account.ordersAvailable) return "Не удалось получить активные ордера Bybit";
  if (account.openOrders.length === 0) return "Активных ордеров нет";
  return `${account.openOrders.length} активных ордеров`;
}

export function connectionStatus(accountStateReady: boolean, ordersReady: boolean, backendConnected: boolean): string {
  if (!backendConnected) return "Backend недоступен";
  if (accountStateReady) return ordersReady ? "Bybit account подключён" : "Bybit account подключён · Открытые ордера временно недоступны";
  return "Приватные данные Bybit недоступны";
}

export function StateView({ account }: { account: AccountState }) {
  const positionLine = (position: AccountState["longPosition"], label: string) => <div><span>{label}</span><b>{position?.size == null ? "нет данных" : qty(position.size)}</b><small>{position?.avgEntryPrice == null ? "средняя цена: нет данных" : `средняя цена: ${price(position.avgEntryPrice)} · uPnL: ${position.unrealizedPnl == null ? "нет данных" : money(position.unrealizedPnl)}`}</small></div>;
  const ordersContent = !account.ordersAvailable ? <div className="empty-inline"><b>{stateOrdersMessage(account)}</b>{account.ordersError && <small>{account.ordersError}</small>}</div> : account.openOrders.length === 0 ? <div className="empty-inline">{stateOrdersMessage(account)}</div> : account.openOrders.map((order, index) => <div className="state-order" key={order.orderId || index}><span className={`mini-dot ${order.side === "Buy" ? "long" : "short"}`}></span><b>{order.side === "Buy" ? "Лонг" : "Шорт"}</b><span>{order.status || "статус не передан"} · {order.price == null ? "цена нет данных" : price(order.price)}</span><strong>{order.leavesQty == null ? "нет данных" : qty(order.leavesQty)}</strong></div>);
  return <section className="state-view"><div className="state-heading"><div><span className="overline">ФАКТЫ АККАУНТА / BYBIT</span><h2>Фактическое состояние</h2><p>Только реальные данные Bybit: позиции, маржа и открытые ордера. План сетки находится в Конструкторе.</p></div><span className="read-only-badge"><ShieldCheck size={14}/> Только чтение</span></div><div className="state-cards"><StateCard label="Доступная маржа" value={money(account.availableMargin)}/><StateCard label="Капитал аккаунта" value={money(account.equity)}/><StateCard label="Начальная маржа" value={money(account.initialMargin)}/><StateCard label="Поддерживающая маржа" value={money(account.maintenanceMargin)}/></div><div className="state-layout"><div className="state-panel"><div className="panel-title"><h3>Наблюдаемая позиция</h3><span>{account.symbol}</span></div><div className="position-table">{positionLine(account.longPosition, "Лонг")}{positionLine(account.shortPosition, "Шорт")}<div><span>Марк-цена</span><b>{price(account.markPrice)}</b><small>валовая экспозиция: {money(account.grossExposure)} · чистая: {money(account.netExposure)}</small></div></div></div><div className="state-panel"><div className="panel-title"><h3>Активные биржевые ордера</h3><span>{account.ordersAvailable ? `${account.openOrders.length} получено` : "недоступно"}</span></div><div className="state-orders">{ordersContent}</div></div></div><div className="connection-card"><div><Wifi size={17}/><div><b>{account.source === "bybit_read_only" ? "Bybit подключён в режиме только чтения" : "Свежих данных нет"}</b><small>Последнее обновление: {account.updatedAt ? new Date(account.updatedAt).toLocaleString("ru-RU") : "нет"}</small></div></div><span className="connection-ok"><Check size={13}/> {account.stale ? "Устарело" : "Доступно"}</span></div></section>;
}

function StateCard({ label, value }: { label: string; value: string }) { return <div className="state-card"><span>{label}</span><b>{value}</b></div>; }
