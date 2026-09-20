# Модель ордера

## Сущности, которые нельзя смешивать

GridOrderConfig → ExchangeOrder → Execution / Fill → StrategyLot / Filled Allocation → TP / Close.

## GridOrderConfig

Намерение стратегии: side, level, geometry reference, configured_qty, planned_notional, TP Steps и Grid Revision.

configured_qty — target, а не факт позиции.

## ExchangeOrder

Конкретная заявка Bybit. Один GridOrderConfig может создавать несколько ExchangeOrder при amend/cancel-replace.

## Execution / Fill

Фактическая сделка на бирже. Execution является источником истины для реально набранного объёма.

## StrategyLot

После первого fill у Grid Order появляется factual allocation.

Пример: configured_qty = 200, filled_qty = 95, open_qty = 95. TP и закрытия считаются от factual open_qty.

Если Entry продолжает получать fills, тот же StrategyLot обновляется.

## Immutable factual history

Новая Grid Revision может изменить будущий configured_qty queued/pending уровней, но не может переписать executions, factual average fill, filled_qty прошлого или realized close history.

## Источник создания

GridOrderConfig может быть manual или generated. После создания execution path одинаковый.
