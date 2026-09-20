# Активное окно ордеров

**Статус: ПОДТВЕРЖДЁННАЯ БАЗОВАЯ МЕХАНИКА**

Полная logical Grid может содержать произвольное количество уровней. На Bybit одновременно держится только configurable subset.

Пример: Full Grid #1..#20, Active Window = 3, на Bybit материализованы #1 #2 #3.

## Связь с dynamic sizing

Queued, ещё не активированные уровни могут получить новый qty после restructuring. Уже выставленный, но неисполненный ExchangeOrder может потребовать amend/cancel-replace, если новая revision меняет его target.

## Связь с geometry

Active Window не меняет геометрию. Оно только решает, какие GridOrderConfig сейчас материализованы на бирже.

## Связь с trailing

Если trailing создаёт новую pending geometry, Active Window reconciliate текущие ExchangeOrders с новой revision. Filled StrategyLots в trailing не участвуют.
