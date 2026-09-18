# Future Execution Engine

**Статус: FUTURE** — не реализуется на текущем этапе, не подключается write-enabled Bybit API.

## Что это будет (концептуально)

Компонент, который в будущем сможет:

- вести учёт Strategy Lots (см. [01-strategy/position-accounting.md](../01-strategy/position-accounting.md));
- отслеживать `take_profit_steps[]` для partial TP (см. [01-strategy/partial-take-profit.md](../01-strategy/partial-take-profit.md));
- поддерживать audit-able редактирование параметров ордеров/lots (before/after/timestamp/reason).

## Что явно не делается сейчас

- Не реализуется trading execution logic.
- Не подключается write-enabled Bybit API key.
- Не размещаются реальные ордера.
- Не реализуется Risk Manager (см. [03-risk/future-risk-manager.md](../03-risk/future-risk-manager.md)).

## Предпосылка для начала работы над этим компонентом

Начало реализации возможно только после того, как достаточное количество правил в [05-research/candidate-rules.md](../05-research/candidate-rules.md) получит статус `CONFIRMED` в [05-research/confirmed-rules.md](../05-research/confirmed-rules.md), и по отдельному явному решению — см. [06-development/decisions.md](../06-development/decisions.md) и [06-development/roadmap.md](../06-development/roadmap.md) (Phase 2+).
