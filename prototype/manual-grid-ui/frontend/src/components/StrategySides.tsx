import { AccountState, Side } from "../domain";

function modeLabel(mode: AccountState["positionMode"]): string {
  return mode === "HEDGE" ? "Hedge Mode" : mode === "ONE_WAY" ? "One-Way" : "Не подтверждён";
}

export function StrategySides({ account, enabledLong, enabledShort, onToggle }: { account: AccountState; enabledLong: boolean; enabledShort: boolean; onToggle: (side: Side) => void }) {
  return <section className="strategy-sides"><div className="strategy-sides-heading"><div><span className="overline">ТОРГОВЫЕ СТОРОНЫ</span><h2>Режим Bybit: {modeLabel(account.positionMode)}</h2></div><span className={`position-mode-badge ${account.positionMode.toLowerCase()}`}>{account.positionMode === "UNKNOWN" ? "Ожидается factual state" : account.positionMode}</span></div><div className="side-toggles"><button type="button" aria-pressed={enabledLong} className={enabledLong ? "selected long" : ""} onClick={() => onToggle("long")}>LONG <b>{enabledLong ? "ON" : "OFF"}</b></button><button type="button" aria-pressed={enabledShort} className={enabledShort ? "selected short" : ""} onClick={() => onToggle("short")}>SHORT <b>{enabledShort ? "ON" : "OFF"}</b></button></div>{account.positionMode === "UNKNOWN" && enabledLong && enabledShort ? <p className="strategy-sides-warning">Не удалось подтвердить Position Mode. Двухсторонняя конфигурация недоступна, пока режим Bybit не подтверждён.</p> : account.positionMode === "ONE_WAY" && enabledLong && enabledShort ? <p className="strategy-sides-warning">Для одновременной Long + Short торговли на Bybit требуется Hedge Mode.</p> : <p className="strategy-sides-note">Стороны сохраняются отдельно для каждого выбранного symbol.</p>}</section>;
}
