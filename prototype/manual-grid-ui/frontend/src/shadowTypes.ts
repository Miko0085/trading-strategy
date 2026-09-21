export type GeneratedSideConfig = {
  enabled: boolean;
  orderCount: number;
  gridDepthPct: number;
  firstOrderOffsetPct: number;
  distributionCoefficient: number;
  leverage: number;
  martingaleCoefficient: number;
  sizingMode: "NORMALIZED_MARTINGALE";
  allocationPct: number;
  activeOrderCount: number;
  tpSteps: Array<{ movePct: number; closePct: number }>;
  trailingEnabled: boolean;
  trailingOffsetPct: number;
  oppositeUpnlReinvestmentPct: number;
  manualOverrides: Array<{ level: number; field: "entry_price" | "qty" | "planned_tp"; value: number | string }>;
};

export type ShadowProposal = {
  mode: string;
  symbol: string;
  capital_snapshot: Record<string, string | null>;
  budgets: Record<string, string>;
  sides: Record<string, { status: string; budget: string; planned_margin?: string; orders: Array<{ level: number; entry_price: string; qty: string; status: string; validation_errors: string[] }> }>;
  validation: { state: string };
};

export function defaultGeneratedSide(enabled: boolean, allocationPct: number): GeneratedSideConfig {
  return { enabled, orderCount: 10, gridDepthPct: 30, firstOrderOffsetPct: 5, distributionCoefficient: 1.5, leverage: 2, martingaleCoefficient: 1.2, sizingMode: "NORMALIZED_MARTINGALE", allocationPct, activeOrderCount: 3, tpSteps: [{ movePct: 10, closePct: 50 }], trailingEnabled: false, trailingOffsetPct: 0, oppositeUpnlReinvestmentPct: 0, manualOverrides: [] };
}
