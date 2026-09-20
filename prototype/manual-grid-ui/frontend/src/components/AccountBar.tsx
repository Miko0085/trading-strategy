import { Clock3 } from "lucide-react";
import { AccountState } from "../domain";
import { money, price } from "../format";
import { SymbolSelector } from "./SymbolSelector";

export function AccountBar({ account, symbols, leverage, onSymbol, onLeverage }: { account: AccountState; symbols: string[]; leverage: number | null; onSymbol: (symbol: string) => void; onLeverage: (value: number | null) => void }) {
  const metric = (label: string, value: string, accent = false) => <div className={`metric ${accent ? "accent" : ""}`}><span>{label}</span><b>{value}</b></div>;
  return <section className="account-strip"><SymbolSelector value={account.symbol} symbols={symbols} onChange={onSymbol}/>{metric("Марк-цена", price(account.markPrice))}{metric("Баланс кошелька", money(account.walletBalance))}{metric("Капитал аккаунта", money(account.equity))}{metric("Доступная маржа", money(account.availableMargin), true)}{metric("Начальная маржа", money(account.initialMargin))}{metric("Поддерживающая маржа", money(account.maintenanceMargin))}<label className="metric leverage-input"><span>Плановый леверидж</span><input inputMode="decimal" type="number" min="1" step="0.1" value={leverage ?? ""} placeholder="укажите" onChange={(event) => onLeverage(event.target.value ? Number(event.target.value) : null)}/></label><div className="updated"><Clock3 size={13}/> Источник: {account.source === "bybit_read_only" ? "Bybit, только чтение" : "нет данных"}<br/>{account.updatedAt ? `Обновлено: ${new Date(account.updatedAt).toLocaleTimeString("ru-RU")}` : "нет обновления"}</div></section>;
}
