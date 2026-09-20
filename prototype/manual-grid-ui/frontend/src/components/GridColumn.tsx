import { ArrowDown, ArrowUp, Plus } from "lucide-react";
import { GridOrder, Side, prices } from "../domain";
import { SideCalculationResult } from "../types";
import { money } from "../format";
import { UtilizationGauge } from "./UtilizationGauge";
import { GridOrderCard } from "./GridOrderCard";

type Guard = { limit: number | null; planned: number | null; remaining: number | null; allowed: boolean };
export function GridColumn({ side, orders, active, mark, tickSize, leverage, guard, calculation, onActive, onAdd, onEdit, onRemove }: { side: Side; orders: GridOrder[]; active: number; mark: number | null; tickSize: number | null; leverage: number | null; guard: Guard; calculation?: SideCalculationResult; onActive: (value: number) => void; onAdd: () => void; onEdit: (id: string, patch: Partial<GridOrder>) => void; onRemove: (id: string) => void }) {
  const previewPrices = prices(mark, side, orders, tickSize);
  const authoritativeOrders = calculation?.orders ?? [];
  const allowed = calculation ? calculation.status === "VALID" : guard.allowed;
  const planned = calculation?.full_grid_planned_margin == null ? guard.planned : Number(calculation.full_grid_planned_margin);
  const limit = calculation?.allocation_limit == null ? guard.limit : Number(calculation.allocation_limit);
  const activeLevels = calculation?.active_window_levels ?? [];
  return <section className={`grid-column ${side}`}><div className="grid-head"><div><div className="side-label"><span className="side-icon">{side === "long" ? <ArrowDown size={15}/> : <ArrowUp size={15}/>}</span><span>{side === "long" ? "ЛОНГ-СЕТКА" : "ШОРТ-СЕТКА"}</span></div><h2>{orders.length} уровней</h2></div><button className="icon-button" aria-label={`Добавить уровень ${side === "long" ? "лонг" : "шорт"}`} onClick={onAdd}><Plus size={17}/></button></div><div className="grid-summary"><span>Полная плановая маржа</span><b className={allowed ? "" : "danger"}>{calculation ? money(planned) : "—"}</b><small>{calculation ? `из ${money(limit)}` : "Заполните параметры"}</small></div><UtilizationGauge side={side} calculation={calculation}/><div className="window-control"><span>Активное окно</span><button type="button" aria-label="Уменьшить активное окно" onClick={() => onActive(Math.max(1, active - 1))}>−</button><input inputMode="numeric" type="number" min="1" max={Math.max(1, orders.length)} value={Math.max(1, active)} onChange={(event) => onActive(Number(event.target.value))}/><button type="button" aria-label="Увеличить активное окно" onClick={() => onActive(Math.min(Math.max(1, orders.length), Math.max(1, active) + 1))}>+</button><span>из {orders.length || 0} уровней</span></div><div className="order-list">{orders.map((order, index) => <GridOrderCard key={order.id} order={order} price={previewPrices[index]} calculated={authoritativeOrders[index]} tickSize={tickSize} leverage={leverage} active={calculation ? activeLevels.includes(order.level) : index < active} onEdit={(patch) => onEdit(order.id, patch)} onRemove={() => onRemove(order.id)}/>)}</div><button className="add-order" onClick={onAdd}><Plus size={15}/> Добавить уровень</button></section>;
}
