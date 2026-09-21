import { Side } from "../domain";
import { SideCalculationResult } from "../types";
import { money, pct } from "../format";

export type RiskMeterModel = { state: "neutral" | "ok" | "danger"; utilization: string; limit: string; activeWindow: string; queue: string; fullGrid: string; remaining: string; excess: string };

export function riskMeterModel(calculation?: SideCalculationResult): RiskMeterModel {
  if (!calculation) return { state: "neutral", utilization: "—", limit: "—", activeWindow: "—", queue: "—", fullGrid: "—", remaining: "—", excess: "—" };
  const excess = Number(calculation.excess ?? 0);
  // A blocked calculation can be caused by a field/order validation error and
  // does not necessarily mean that the capital limit was exceeded. The meter
  // turns danger only for factual excess; otherwise its gradient reflects the
  // actual utilization percentage.
  return { state: excess > 0 ? "danger" : "ok", utilization: pct(Number(calculation.utilization_pct ?? 0)), limit: money(Number(calculation.allocation_limit)), activeWindow: money(Number(calculation.active_window_planned_margin)), queue: money(Number(calculation.queued_planned_margin)), fullGrid: money(Number(calculation.full_grid_planned_margin)), remaining: money(Number(calculation.remaining_limit)), excess: excess > 0 ? money(excess) : "—" };
}

export function UtilizationGauge({ side, calculation }: { side: Side; calculation?: SideCalculationResult }) {
  const model = riskMeterModel(calculation);
  const value = calculation ? Math.min(100, Math.max(0, Number(calculation.utilization_pct ?? 0))) : 0;
  const progressDegrees = `${value * 1.8}deg`;
  const needleAngle = `${-90 + value * 1.8}deg`;
  return <div className={`risk-meter ${model.state}`} data-testid={`risk-meter-${side}`}><div className="risk-arc" data-testid="risk-arc" style={{ "--risk-progress": progressDegrees, "--risk-angle": needleAngle } as React.CSSProperties}><div className="risk-arc-inner"><strong>{model.utilization}</strong><span>использование<br/>лимита</span></div><div className="risk-needle" data-testid="risk-needle"><i/></div></div><b>Использование лимита {side === "long" ? "Лонг" : "Шорт"}</b><div className="risk-grid"><span>Лимит <strong data-testid="risk-limit">{model.limit}</strong></span><span>Активное окно <strong data-testid="risk-active-window">{model.activeWindow}</strong></span><span>Очередь <strong data-testid="risk-queue">{model.queue}</strong></span><span>Полная сетка <strong data-testid="risk-full-grid">{model.fullGrid}</strong></span><span>Остаток <strong data-testid="risk-remaining">{model.remaining}</strong></span><span>Превышение <strong data-testid="risk-excess">{model.excess}</strong></span></div>{!calculation && <small>Заполните параметры сетки</small>}{model.state === "danger" && <small className="danger">Точное превышение: {model.excess}</small>}</div>;
}
