# State Machine (сводная)

**Статус: CANDIDATE / FUTURE** — черновая схема для будущей формализации, не текущая работающая система.

## Уровень ордера

```
PLACED → (FILLED | PARTIALLY_FILLED | CANCELLED | REJECTED)
```

## Уровень Strategy Lot (FUTURE, ещё не реализовано)

```
CREATED (при execution) 
  → OPEN (remaining_qty == original_qty)
  → PARTIALLY_CLOSED (0 < remaining_qty < original_qty)
  → CLOSED (remaining_qty == 0)
```

Переходы `OPEN → PARTIALLY_CLOSED → CLOSED` управляются срабатыванием `take_profit_steps[]` (см. [01-strategy/partial-take-profit.md](../01-strategy/partial-take-profit.md)). Ни разу не наблюдался переход через `PARTIALLY_CLOSED` в реальных данных — единственное известное закрытие было прямым `OPEN → CLOSED`.

## Уровень Grid (LONG GRID / SHORT GRID)

```
CONFIGURED → ACTIVE (есть хотя бы один открытый Grid Order или Lot)
  → RESTRUCTURING (гипотетически, триггер не подтверждён)
  → EMPTY (все lots закрыты, все ордера отменены/исполнены)
```

`RESTRUCTURING` — гипотетическое состояние, добавлено для полноты диаграммы, не подтверждено как формальный шаг. См. [05-research/open-questions.md](../05-research/open-questions.md).
