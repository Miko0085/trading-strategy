# Roadmap

**Статус: FUTURE / TRADER EXPLANATION**

## Главный принцип очерёдности

> Сначала фиксируем реальную механику. Потом подтверждаем правила. Потом формализуем алгоритм. Потом тестируем. И только потом автоматизируем торговые решения.

Не оптимизировать стратегию "от себя", не предсказывать рынок, не добавлять внешние сигналы, не превращать примеры трейдера в правила без подтверждения (см. [00-overview/principles.md](../00-overview/principles.md)).

## Фазы

### Phase 1 — Base Strategy Mechanics (текущая)

Формализация механики: Long/Short, Hedge Mode, Grid Orders, coin quantity, order spacing, Strategy Lots, partial TP, partial unloading, order/grid lifecycle, ручное изменение параметров. См. [00-overview/goals.md](../00-overview/goals.md).

### Phase 2 — Formalization / Testing

Превращение накопленных `CONFIRMED` правил ([05-research/confirmed-rules.md](../05-research/confirmed-rules.md)) в проверяемый алгоритм и его тестирование на исторических данных Recorder'а. Не начинается, пока не закрыта значимая часть [open-questions.md](../05-research/open-questions.md).

### Phase 3 — Risk Manager

См. [03-risk/future-risk-manager.md](../03-risk/future-risk-manager.md). Не реализуется раньше формализации базовой механики.

### Phase 4 — Additional internal managers/helpers

Не детализировано на текущем этапе.

## Recorder не в этом roadmap

Recorder — уже реализованный, отдельный технический слой (см. [04-platform/recorder-role.md](../04-platform/recorder-role.md)). Его развитие фиксируется отдельно в корневом [`DEVELOPMENT_STATUS.md`](../../DEVELOPMENT_STATUS.md), не здесь.
