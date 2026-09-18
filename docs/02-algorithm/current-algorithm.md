# Текущий алгоритм

**Статус: CONFIRMED (структура flow) — без decision logic**

Ниже — только подтверждённая последовательность шагов ручного процесса трейдера. Это **не** исполняемый алгоритм и не содержит формул принятия решений, которые пока не подтверждены (глубина сетки, sizing, TP-уровни и т.д. — см. соответствующие документы в [01-strategy/](../01-strategy/strategy-overview.md) и [05-research/open-questions.md](../05-research/open-questions.md)).

```
START
  ↓
Select Symbol
  ↓
Configure Long Grid
  ↓
Configure Short Grid
  ↓
Define Grid Limit Prices
  ↓
Define Coin Qty per Order
  ↓
Define TP configuration
  ↓
Place/observe Limit Orders
  ↓
Order Executes
  ↓
Create Strategy Lot
  ↓
Track Lot Independently
  ↓
Price reaches Lot TP
  ↓
Close configured coin quantity
  ↓
Update remaining_qty
  ↓
Continue
```

## Что этот flow не определяет

- Как именно выбирается qty каждого следующего Grid Order (см. [05-research/open-questions.md](../05-research/open-questions.md), вопрос 1).
- Формулу spacing по глубине (вопрос 2).
- Условие/момент перестройки сетки (вопрос 3).
- Что происходит с remaining_qty после всех запланированных TP (вопрос 5).
- Наличие обязательного финального TP или Stop Loss (вопросы 6, 7).

## Связанные документы

- [order-lifecycle.md](order-lifecycle.md) — состояния одного ордера.
- [grid-lifecycle.md](grid-lifecycle.md) — состояния сетки целиком.
- [state-machine.md](state-machine.md) — сводная state machine.
