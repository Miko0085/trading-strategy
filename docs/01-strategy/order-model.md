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

## 1. GridOrderConfig — intent конкретного уровня

Минимально хранит:
- `id`;
- `side`: LONG | SHORT;
- `level`;
- `entry_input_mode`: PRICE | PERCENT;
- `entry_price` / `offset_pct`;
- `configured_qty`;
- `filled_qty`;
- `remaining_entry_qty`;
- `manual_qty_lock`;
- TP1..TP4 config;
- source / revision.

Sizing parameters разделены на side-level и order-level.

### Side-level

```text
sizing_mode: POWER_CURVE | PER_ORDER_M
power_k?      # только POWER_CURVE
leverage
```

### Order-level

```text
martingale_multiplier?  # M_i только PER_ORDER_M
raw_weight
normalized_weight
planned_margin
planned_notional
```

В `POWER_CURVE` отдельный `M_i` не требуется.

В `PER_ORDER_M` каждый переход может иметь собственный multiplier; `M_i=1` означает отсутствие увеличения веса.

## 2. Planned qty не является factual fill

В основном Manual Grid qty рассчитывается sizing layer:

```text
planned_notional_i
/ entry_price_i
= raw_qty_i
→ qtyStep normalization
= remaining_entry_qty / configured_qty intent
```

Это всё ещё intent до фактического Execution.

## 3. ExchangeOrder

Конкретная биржевая заявка Bybit с exchange order ID / orderLinkId и runtime state.

Один GridOrderConfig может порождать несколько ExchangeOrders во времени при amend/cancel-replace.

Не каждый GridOrderConfig одновременно имеет ExchangeOrder: Active Order Window держит часть уровней queued.

## 4. Execution / Fill

Execution — ground truth фактической сделки.

Один ExchangeOrder может иметь несколько executions. Они не создают новые Grid Orders.

## 5. StrategyLot / Filled Allocation

Появляется после первого factual fill.

```text
configured_qty = 1.0
fill #1 = 0.3

filled_qty = 0.3
remaining_entry_qty = 0.7
```

Последующие fills обновляют тот же StrategyLot и quantity-weighted average fill.

## 6. Factual и future части

```text
filled_qty / open_qty
→ factual, immutable

remaining_entry_qty
→ future intent, resizable
```

Всегда:

```text
configured_qty = filled_qty + remaining_entry_qty
configured_qty >= filled_qty
```

## 7. TP

У StrategyLot максимум четыре TP parts.

TP quantities не могут суммарно превышать factual `open_qty`.

## 8. Restructuring

Поддерживаются:

```text
RECALCULATE_ORDER
RECALCULATE_GRID
```

- `RECALCULATE_ORDER` меняет future intent выбранного уровня;
- `RECALCULATE_GRID` заново генерирует weights выбранным sizing mode и распределяет весь eligible future budget стороны.

Profit-taking event может инициировать новый restructuring proposal, но routing капитала между сторонами определяется отдельной политикой.

## 9. Technical validation state

GridOrderConfig/plan должен хранить результат pre-execution validation, например:

```text
VALID
BELOW_MIN_ORDER_QTY
BELOW_MIN_NOTIONAL
INVALID_QTY_STEP
INVALID_TICK_SIZE
STALE_INSTRUMENT_METADATA
MANUAL_REVIEW
```

Если один обязательный order общего плана невалиден, partial apply запрещён.

## 10. Audit

Каждая существенная правка сохраняет:
- before / after;
- timestamp;
- source;
- Grid Revision;
- sizing mode / coefficient;
- restructuring reason;
- instrument metadata snapshot reference;
- связь с ExchangeOrder / Execution / StrategyLot.

Цепочка должна быть восстанавливаема:

```text
INTENT
→ SIZING
→ VALIDATION
→ EXCHANGE ORDER
→ EXECUTION
→ FACTUAL LOT
→ NEW FUTURE INTENT
```
