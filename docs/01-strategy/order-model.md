# Модель ордера

## Сущности, которые нельзя смешивать

```text
GridOrderConfig
    ↓
ExchangeOrder
    ↓
Execution / Fill
    ↓
StrategyLot / Filled Allocation
    ↓
TP / Partial Close / Full Close
```

## 1. GridOrderConfig — намерение трейдера

Хранит как минимум:
- номер уровня;
- Long / Short;
- `entry_input_mode`: PRICE | PERCENT;
- `entry_price` и/или `offset_pct`;
- `martingale_multiplier` конкретного уровня;
- `configured_qty`;
- `filled_qty`;
- `remaining_entry_qty`;
- TP Steps;
- source / sizing source;
- revision конфигурации.

Для основного Manual Grid трейдер задаёт геометрию и per-order Martingale, а `configured_qty`/`remaining_entry_qty` рассчитываются системой.

Это описание того, **что система собирается сделать**, а не факт исполнения.

## 2. Per-Order Martingale

В Manual Grid коэффициент уровня относится к предыдущему весу:

```text
w1 = 1
w2 = w1 × M2
w3 = w2 × M3
...
```

Коэффициент является частью intent конкретного GridOrderConfig.

## 3. ExchangeOrder — реальная заявка на Bybit

Это конкретная биржевая заявка с собственным exchange order ID и состоянием.

Один GridOrderConfig может порождать одну или несколько ExchangeOrders в течение жизненного цикла, например после amend/cancel-replace.

Не все GridOrderConfig одновременно обязаны иметь ExchangeOrder: Active Order Window может держать часть уровней в очереди внутри платформы.

## 4. Execution / Fill — факт сделки

Execution — фактическое исполнение на бирже.

Один ExchangeOrder может иметь несколько executions. Они не создают новые Grid Orders.

## 5. StrategyLot / Filled Allocation

После первого factual fill система отдельно учитывает исполненный объём конкретного Grid Order.

```text
configured_qty = 1.0
fill #1 = 0.3

filled_qty = 0.3
remaining_entry_qty = 0.7
```

После следующего fill:

```text
fill #2 = 0.2
filled_qty = 0.5
```

Это тот же логический StrategyLot.

## 6. Factual и future части нельзя смешивать

```text
filled_qty / open_qty
→ factual reality
→ не пересчитывается реструктуризацией объёма

remaining_entry_qty
→ future intent
→ может быть изменён
```

`configured_qty` после реструктуризации может измениться только так, чтобы не нарушалось:

```text
configured_qty >= filled_qty
configured_qty = filled_qty + remaining_entry_qty
```

## 7. Restructuring scope

Для volume restructuring используются два режима:

```text
RECALCULATE_ORDER
RECALCULATE_GRID
```

Точечный режим меняет future intent одного ордера. Полный режим может изменить future qty всех eligible pending levels стороны.

## 8. Закрытия

TP или manual close изменяют:
- `open_qty`;
- `closed_qty`;
- realized PnL конкретного StrategyLot.

## 9. История изменений

Любая существенная правка через интерфейс должна сохранять:
- before;
- after;
- timestamp;
- source;
- Grid Revision;
- restructuring scope/reason, если применимо;
- связь с ExchangeOrder / Execution / StrategyLot.

Цель — всегда восстановить цепочку:

```text
INTENT → PLANNED QTY → EXCHANGE ORDER → FILL → FACTUAL LOT → RESTRUCTURED FUTURE INTENT
```
