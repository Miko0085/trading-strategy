# Confirmed Rules

**Статус: CONFIRMED** — правила в этом файле явно подтверждены трейдером. Список короткий и намеренно строгий: см. правило в [06-development/decisions.md](../06-development/decisions.md) — никогда не повышать `CANDIDATE` до `CONFIRMED` без явного подтверждения.

## 1. Coin quantity — основная единица объёма

Primary size unit = coin quantity, не долларовая маржа. USDT notional, margin и PnL — производные величины. См. [01-strategy/position-accounting.md](../01-strategy/position-accounting.md).

## 2. TP считается от цены исполнения конкретного lot

Partial TP для Strategy Lot считается относительно **actual average execution price этого lot**, а не относительно общей average entry Long/Short, не относительно предыдущего TP и не относительно начальной цены рынка. См. [01-strategy/partial-take-profit.md](../01-strategy/partial-take-profit.md).

## 3. Close percentage считается от original_qty lot

Процент частичного закрытия (partial TP) считается от `original_qty` конкретного lot, а не от текущего `remaining_qty` на момент срабатывания следующего TP. См. [01-strategy/partial-take-profit.md](../01-strategy/partial-take-profit.md).

## 4. Никаких внешних сигналов в базовой стратегии

Индикаторы, новости, sentiment, AI-прогнозы не используются как вход для решений стратегии. См. [00-overview/principles.md](../00-overview/principles.md) — это project-wide правило.

## 5. Grid Orders — лимитные ордера с конфигурируемым spacing

Следующий уровень сетки рассчитывается от цены предыдущего лимитного ордера (не от исходной reference price), не дожидаясь его исполнения. Конкретные проценты spacing не фиксированы как правило — только сам механизм расчёта. См. [01-strategy/grid-mechanics.md](../01-strategy/grid-mechanics.md).

---

Всё остальное, что напоминает правило, но не подтверждено явно — в [candidate-rules.md](candidate-rules.md).
