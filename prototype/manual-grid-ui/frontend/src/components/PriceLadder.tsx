import { AccountState, GridOrder, prices } from "../domain";
import { CalculationResult } from "../types";
import { price } from "../format";

export function PriceLadder({ account, long, short, tickSize, calculation }: { account: AccountState; long: GridOrder[]; short: GridOrder[]; tickSize: number | null; calculation?: CalculationResult | null }) {
  const ladder = ladderPrices(account, long, short, tickSize, calculation);
  const longPrices = ladder.long;
  const shortPrices = ladder.short;
  return <div className="ladder"><div className="ladder-title">Лестница цен <small>{calculation ? "Расчёт подтверждён backend" : "Предварительный расчёт"}</small></div>{shortPrices.slice().reverse().map((value, index) => <div className="rung short-rung" key={`s${index}`}><span>ШОРТ #{shortPrices.length - index}</span><b>{price(value)}</b></div>)}<div className="mark-line"><i></i><span>Марк-цена</span><b>{price(account.markPrice)}</b></div>{longPrices.map((value, index) => <div className="rung long-rung" key={`l${index}`}><span>ЛОНГ #{index + 1}</span><b>{price(value)}</b></div>)}</div>;
}

export function ladderPrices(account: AccountState, long: GridOrder[], short: GridOrder[], tickSize: number | null, calculation?: CalculationResult | null): { long: number[]; short: number[]; source: "backend" | "preview" } {
  return calculation ? { long: calculation.long.orders.map((order) => Number(order.planned_entry_price)), short: calculation.short.orders.map((order) => Number(order.planned_entry_price)), source: "backend" } : { long: prices(account.markPrice, "long", long, tickSize).filter((value): value is number => value != null), short: prices(account.markPrice, "short", short, tickSize).filter((value): value is number => value != null), source: "preview" };
}
