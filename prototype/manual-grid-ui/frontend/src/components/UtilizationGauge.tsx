import { Side } from "../domain";
import { SideCalculationResult } from "../types";
import { money, pct } from "../format";

export function riskMeterModel(calculation?: SideCalculationResult): { state: "neutral" | "ok" | "danger"; utilization: string; limit: string; planned: string; remaining: string; excess: string } {
  if (!calculation) return { state: "neutral", utilization: "—", limit: "—", planned: "—", remaining: "—", excess: "—" };
  const excess = Number(calculation.excess ?? 0);
  return { state: excess > 0 || calculation.status === "BLOCKED" ? "danger" : "ok", utilization: pct(Number(calculation.utilization_pct ?? 0)), limit: money(Number(calculation.allocation_limit)), planned: money(Number(calculation.full_grid_planned_margin)), remaining: money(Number(calculation.remaining_limit)), excess: excess > 0 ? money(excess) : "—" };
}

export function UtilizationGauge({ side, calculation }: { side: Side; calculation?: SideCalculationResult }) {
  const model = riskMeterModel(calculation);
  const value = calculation ? Math.min(100, Math.max(0, Number(calculation.utilization_pct ?? 0))) : 0;
  return <div className={`risk-meter ${model.state}`} data-testid={`risk-meter-${side}`}><div className="risk-arc" style={{ "--risk-progress": `${value}%` } as React.CSSProperties}><strong>{model.utilization}</strong><span>использование<br/>лимита</span></div><b>Использование лимита {side === "long" ? "Лонг" : "Шорт"}</b><div className="risk-grid"><span>Лимит <strong>{model.limit}</strong></span><span>Активное окно <strong>{model.planned}</strong></span><span>Остаток <strong>{model.remaining}</strong></span><span>Превышение <strong>{model.excess}</strong></span></div>{!calculation && <small>Заполните параметры сетки</small>}{model.state === "danger" && <small className="danger">Точное превышение: {model.excess}</small>}</div>;
}
