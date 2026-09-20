# Механика сетки

**Статус: ПОДТВЕРЖДЁННАЯ БАЗОВАЯ МЕХАНИКА**

## Два режима построения

### Manual Grid
Трейдер вручную задаёт для каждого Grid Order offset, configured qty и TP Steps.

### Generated Grid
Система автоматически создаёт произвольное количество уровней на заданной глубине.

Базовые входы: order_count, grid_depth_pct, first_order_offset_pct, distribution_coefficient, initial sizing parameters и martingale coefficient.

Количество уровней не фиксируется десятью. Десять — только типовой пример.

## Геометрия и объём

Generated Grid сначала строит Grid Geometry, затем sizing. Martingale относится к sizing, а не к расстояниям.

Объём может быть задан вручную в монетах или сгенерирован sizing-механикой из бюджета и Martingale curve. Execution Engine в обоих случаях получает конкретный configured_qty.

## Частичное исполнение

Пример: configured_qty = 200, фактически исполнилось 40 + 55. filled_qty = 95. Фактический объём стратегии равен 95, а не 200.

Неисполненный остаток Entry Order не является позицией и не участвует в TP.

## Активное окно

Полная logical grid может содержать десятки уровней, но на Bybit одновременно выставляется только configurable Active Order Window. Queued levels могут получить новый qty после реструктуризации до фактического исполнения.

## Изменение сетки

Новая revision может менять будущие уровни и qty, но никогда не переписывает реальные executions.
