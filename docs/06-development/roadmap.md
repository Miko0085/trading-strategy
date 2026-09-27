# План разработки

## Основной принцип

Исследование стратегии, sizing, execution и risk развиваются параллельно, но autonomous decisions нельзя реализовывать раньше подтверждения правил.

Текущий продуктовый приоритет — Manual Grid с двумя sizing modes, hard Bybit validation и manual/full-grid restructuring.

## Этап 1A — Recorder / Strategy Capture

- machine truth Bybit;
- trader explanations;
- timeline;
- intent ↔ factual events;
- restructuring observations;
- подтверждение rules.

Recorder permanently read-only.

## Этап 1B — Manual Grid + Sizing

Реализовать:
- Long/Short independent Grid;
- GridRevision / GridOrderConfig;
- Entry PRICE | PERCENT;
- `POWER_CURVE` side-level sizing;
- `PER_ORDER_M` advanced sizing;
- Future Margin Budget → Notional → Qty;
- instrument normalization;
- max 4 TP parts;
- StrategyLot after first fill;
- Active Order Window.

Не добавлять отдельные Linear/Equal/Reverse/Global-Geometric modes в MVP.

## Этап 1C — Instrument Metadata + Hard Validation

- Bybit Instruments Info;
- local InstrumentSpec cache;
- refresh/freshness policy;
- `minOrderQty`;
- `qtyStep`;
- `minNotionalValue`;
- `tickSize`;
- atomic `MANUAL_REVIEW` if any mandatory order invalid.

## Этап 1D — Manual Volume Restructuring

- `RECALCULATE_ORDER`;
- `RECALCULATE_GRID`;
- add level during active Grid;
- immutable factual fills;
- locked future qty;
- before/after preview;
- Grid Revision;
- recalculation by selected sizing mode.

## Этап 1E — Profit-Taking Trigger

- profitable TP/close event;
- fresh account snapshot;
- deduplicated restructuring trigger;
- new sizing proposal;
- no automatic cross-side routing until rule confirmed.

## Этап 1F — Execution Engine Core

- ApprovedExecutionPlan;
- idempotent ExecutionCommand;
- PLACE/AMEND/CANCEL/CLOSE;
- Active Window runtime;
- WS/REST reconciliation;
- orderLinkId correlation;
- duplicate/out-of-order handling;
- restart recovery;
- testnet/demo-first.

## Этап 1G — Reinvestment Routing Research

Исследовать:
- same-side;
- cross-side risk-priority;
- both-side;
- production `capital_base`;
- reinvestable capital definition;
- liquidation/risk priority;
- recovery;
- trailing/rebase.

## Этап 2 — Simulation / Shadow / Testnet

Проверить:
- Power Curve;
- Per-Order M;
- budget changes;
- minimum-lot failures;
- partial fills;
- 4 TP parts;
- Active Window;
- restructuring;
- external intervention;
- network/API races;
- restart/reconciliation.

## Этап 3 — Risk Manager

- capital/margin/exposure limits;
- reserve;
- liquidation distance;
- ALLOW/MODIFY/DENY;
- emergency states.

## Этап 4 — Controlled Real Execution

Только отдельным решением:
- production write key;
- hard limits;
- kill switch;
- limited rollout;
- audit/reconciliation.

## Этап 5 — Controlled Autonomous Restructuring

Только после подтверждения routing/risk rules:
- automatic application after profitable TP;
- automatic Long/Short routing;
- recovery;
- rebase/trailing;
- automatic Grid revisions.
