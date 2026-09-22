export type GeneratedSideConfig = {
  enabled: boolean;
  orderCount: number;
  gridDepthPct: number;
  firstOrderOffsetPct: number;
  distributionCoefficient: number;
  logarithmicDistributionEnabled: boolean;
  leverage: number;
  martingaleMultiplier: number;
  sizingMode: "NORMALIZED_MARTINGALE";
  activeOrderCount: number;
  tpSteps: Array<{ movePct: number; closePct: number }>;
  trailingEnabled: boolean;
  trailingOffsetPct: number;
  realizedReinvestPct: number;
  longUnrealizedReinvestPct: number;
  shortUnrealizedReinvestPct: number;
  manualOverrides: Array<{ level: number; field: "entry_price" | "qty" | "planned_tp"; value: number | string }>;
};

export type ShadowProposal = {
  mode: string;
  symbol: string;
  capital_snapshot: Record<string, string | null>;
  budgets: Record<string, string>;
  sides: Record<string, { status: string; validation_state?: string; budget: string; active_order_count?: number; planned_margin?: string; orders: Array<{ level: number; entry_price: string; qty: string; filled_qty?: string; actual_avg_fill?: string | null; planned_tp?: Array<{ move_pct?: string; close_pct?: string; price?: string }>; source?: string; manual_price_lock?: boolean; manual_qty_lock?: boolean; validation_errors: string[] }> }>;
  validation: { state: string };
};

export function defaultGeneratedSide(enabled: boolean): GeneratedSideConfig {
  return { enabled, orderCount: 10, gridDepthPct: 30, firstOrderOffsetPct: 5, distributionCoefficient: 1.5, logarithmicDistributionEnabled: true, leverage: 2, martingaleMultiplier: 1.2, sizingMode: "NORMALIZED_MARTINGALE", activeOrderCount: 3, tpSteps: [{ movePct: 10, closePct: 50 }], trailingEnabled: false, trailingOffsetPct: 0, realizedReinvestPct: 0, longUnrealizedReinvestPct: 0, shortUnrealizedReinvestPct: 0, manualOverrides: [] };
}
