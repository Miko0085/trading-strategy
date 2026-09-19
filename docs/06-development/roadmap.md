# План разработки

## Основной принцип

Исследование стратегии, доменная модель и механический execution могут развиваться параллельно, но autonomous decisions нельзя реализовывать раньше подтверждения правил.

## Этап 1A — Recorder / Strategy Capture

- machine truth Bybit;
- trader explanations;
- timeline;
- связь intent и фактических событий;
- restructuring observations;
- выявление и подтверждение правил.

Recorder остаётся permanently read-only.

## Этап 1B — Domain Model + Base Grid Mechanics

Формализовать:
- Grid;
- GridRevision;
- GridOrderConfig;
- ExchangeOrder;
- Execution;
- StrategyLot;
- TPStep;
- Active Order Window;
- lifecycle/state machines;
- partial fill semantics;
- TP mechanics.

Без real write execution.

## Этап 1C — Execution Engine Core

Сделать детерминированный исполнительный слой:
- ApprovedExecutionPlan;
- ExecutionCommand;
- Bybit validation;
- idempotency;
- audit;
- reconciliation;
- restart recovery;
- paper/shadow mode.

## Этап 1D — Restructuring Research

Параллельно:
- capture ручных реструктуризаций;
- Capital Recalculation;
- Volume Recovery;
- Grid Restructuring;
- compound logic;
- allocation;
- триггеры rebase;
- RestructuringPlan.

На этом этапе правила исследуются, но не исполняются автономно.

## Этап 2 — Simulation / Shadow / Testnet

- воспроизводить Base Grid;
- проигрывать RestructuringPlan без реального риска;
- сравнивать решения с трейдером;
- учитывать fees/funding/slippage/partial fills;
- проверять restart/reconciliation.

## Этап 3 — Risk Manager

Реализовать отдельный gate:
- ALLOW;
- MODIFY;
- DENY;
- capital/margin/exposure limits;
- margin reserve;
- safety states.

## Этап 4 — Controlled Real Execution

Только отдельным решением:
- production write-enabled key;
- hard limits;
- emergency controls;
- ограниченный rollout;
- обязательный audit/reconciliation.

## Этап 5 — Controlled Autonomous Strategy Decisions

Только после подтверждения и тестирования:
- автоматические restructuring triggers;
- automatic capital recalculation;
- volume recovery rules;
- automatic Grid revisions.

Неизвестные правила нельзя заполнять предположениями.