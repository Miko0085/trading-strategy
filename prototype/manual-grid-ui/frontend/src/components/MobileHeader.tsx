import { Wifi } from "lucide-react";
import { AccountState } from "../domain";
import { price } from "../format";
import { SymbolSelector } from "./SymbolSelector";

export function MobileHeader({ account, environment, connected, symbols, onSymbol }: { account: AccountState; environment: "mainnet" | "testnet" | null; connected: boolean; symbols: string[]; onSymbol: (symbol: string) => void }) {
  return <header className="mobile-header"><div className="mobile-header-main"><div><b>{account.symbol}</b><span>{environment === "testnet" ? "TESTNET" : "MAINNET"} · Только чтение</span></div><span className={`mobile-live ${connected && !account.stale ? "online" : "offline"}`}><i></i>{connected && !account.stale ? "LIVE" : "НЕТ СВЯЗИ"}</span></div><div className="mobile-header-meta"><span>Mark <strong>{price(account.markPrice)}</strong></span><span><Wifi size={13}/> {connected ? "Bybit" : "Backend недоступен"}</span></div><div className="mobile-symbol-selector"><SymbolSelector value={account.symbol} symbols={symbols} onChange={onSymbol}/></div></header>;
}
