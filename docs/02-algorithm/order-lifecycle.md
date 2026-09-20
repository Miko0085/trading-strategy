# Жизненные циклы ордеров

**Статус: БАЗОВАЯ ДОМЕННАЯ МОДЕЛЬ**

## GridOrderConfig

CONFIGURED → ACTIVE → PARTIALLY_FILLED → FILLED. Возможны DISABLED/REMOVED или superseded by new Grid Revision.

## ExchangeOrder

New → PartiallyFilled → Filled; New/PartiallyFilled → Cancelled; New → Rejected.

## Partial fill invariant

После первого Execution factual position allocation уже существует.

Пример: configured_qty = 200, filled_qty = 95, remaining entry qty = 105. StrategyLot работает от 95. Оставшиеся 105 не считаются позицией.

Если новая revision меняет target future qty, уже произошедшие executions остаются неизменными.

## Главное разделение

GridOrderConfig ≠ ExchangeOrder ≠ Execution ≠ StrategyLot.
