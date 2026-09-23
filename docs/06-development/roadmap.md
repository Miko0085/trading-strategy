# План разработки

## Основной принцип

Исследование стратегии, доменная модель и механический execution развиваются параллельно, но autonomous decisions нельзя реализовывать раньше подтверждения правил.

Текущий продуктовый приоритет — Manual Grid с автоматическим future sizing и ручной реструктуризацией объёма.

## Этап 1A — Recorder / Strategy Capture

- machine truth Bybit;
- trader explanations;
- timeline;
- связь intent и фактических событий;
- restructuring observations;
- подтверждение правил.

Recorder остаётся permanently read-only.

## Этап 1B — Manual Grid Domain + Sizing

Формализовать и реализовать:
- Grid / GridRevision;
- GridOrderConfig;
- Entry input PRICE | PERCENT;
- per-order Martingale multiplier;
- cumulative Martingale chain;
- automatic future qty from side budget;
- factual used capital accounting;
- remaining_entry_qty;
- Active Order Window;
- StrategyLot / partial fill semantics;
- TP mechanics;
- Bybit instrument normalization.

Generated Grid остаётся optional constructor и не блокирует этот этап.

## Этап 1C — Manual Volume Restructuring

Реализовать сначала в shadow/read-only режиме:

- `RECALCULATE_ORDER`;
- `RECALCULATE_GRID`;
- добавление новых уровней в существующую сетку;
- пересчёт только future/pending qty;
- immutable factual fills;
- before/after audit;
- новая Grid Revision;
- validation against current side budget and Bybit limits.

Автоматические triggers на этом этапе не нужны.

## Этап 1D — Execution Engine Core

Сделать детерминированный исполнительный слой:
- ApprovedExecutionPlan;
- ExecutionCommand;
- Bybit validation;
- idempotency;
- audit;
- reconciliation;
- restart recovery;
- paper/testnet-first;
- Active Order Window runtime.

## Этап 1E — Restructuring Research

Параллельно исследовать только неподтверждённую автоматику:
- automatic triggers;
- recovery после разгрузки;
- reinvestment triggers;
- rebase/trailing policy;
- exact production capital_base;
- automatic allocation changes.

## Этап 2 — Simulation / Shadow / Testnet

- воспроизводить Manual Grid;
- проверять per-order sizing;
- проигрывать `RECALCULATE_ORDER` и `RECALCULATE_GRID`;
- проверять partial fills;
- добавлять новые levels во время cycle;
- сравнивать планы с действиями трейдера;
- учитывать fees/funding/slippage;
- проверять restart/reconciliation.

## Этап 3 — Risk Manager

Реализовать отдельный gate:
- ALLOW;
- MODIFY;
- DENY;
- capital/margin/exposure limits;
- reserve;
- safety states.

## Этап 4 — Controlled Real Execution

Только отдельным решением:
- production write-enabled key;
- hard limits;
- emergency controls;
- limited rollout;
- обязательный audit/reconciliation.

## Этап 5 — Controlled Autonomous Strategy Decisions

Только после подтверждения и тестирования:
- automatic restructuring triggers;
- automatic reinvest;
- volume recovery rules;
- automatic rebase/trailing;
- automatic Grid revisions.

Неизвестные правила нельзя заполнять предположениями.
