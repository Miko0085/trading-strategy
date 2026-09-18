# Roadmap

## Основной принцип

> Сначала фиксируем реальную механику. Потом подтверждаем неизвестные decision rules. Механическое исполнение заранее заданной конфигурации может развиваться параллельно с исследованием. Автономные решения и Risk Manager — только после формализации и тестирования.

## Phase 1A — Strategy Capture / Recorder

Продолжать:

- записывать Bybit machine truth;
- сохранять trader explanations;
- связывать действия и контекст;
- выявлять candidate rules;
- подтверждать/опровергать гипотезы.

Recorder остаётся read-only.

## Phase 1B — Base Strategy Mechanics

Формализовать и затем технически реализовать отдельно от Recorder:

- Long Grid / Short Grid;
- configurable N Grid Orders;
- limit price chain;
- coin quantity per order;
- Strategy Lot accounting;
- partial TP steps;
- remaining_qty;
- ручное редактирование/отмена конфигурации;
- audit trail.

Эта фаза **не обязана ждать полной формализации decision logic**, потому что параметры задаёт трейдер.

## Phase 2 — Shadow / Simulation / Testing

- воспроизводить механику без реального риска;
- сравнивать расчётные действия с действиями трейдера;
- тестировать confirmed rules;
- проверять path-dependent сценарии;
- учитывать fees/funding/slippage/partial fills.

## Phase 3 — Risk Manager

Добавить отдельный слой контроля:

- margin/equity;
- gross/side exposure;
- allocation limits;
- risk states;
- forced/early unloading только после подтверждения правил.

Risk Manager не прогнозирует рынок и не использует внешние indicators/news/sentiment.

## Phase 4 — Controlled Automated Execution

Только отдельным решением после тестирования:

- write-enabled API в отдельном Execution Engine;
- hard safety limits;
- emergency controls;
- постепенный rollout.

## Phase 5 — Additional internal managers/helpers

Детализируется позже.
