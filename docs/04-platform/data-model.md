# Модель данных

**Статус: RECORDER РЕАЛИЗОВАН / MANUAL GRID, SIZING И RESTRUCTURING MODEL ФОРМАЛИЗОВАНЫ ЧАСТИЧНО**

## 1. Recorder — factual reality

Recorder хранит machine truth:
- orders;
- executions;
- positions;
- closed_pnl;
- funding;
- current_states;
- observations;
- timeline;
- trader_notes;
- tracked_instruments.

Recorder остаётся read-only и не является operational DB будущего Execution Engine.

## 2. Grid

Долгоживущая сущность одной стороны:

```text
Grid
- symbol
- side: LONG | SHORT
- status
- current_revision_id
```

Long и Short являются независимыми Grid.

## 3. GridRevision

Immutable snapshot intent:
- reference market snapshot;
- allocation;
- leverage;
- sizing mode;
- Power Curve `K` или per-order `M_i`;
- active order count;
- GridOrderConfig;
- TP configs;
- instrument metadata snapshot reference;
- before/after context;
- reason/trigger.

## 4. GridOrderConfig

Минимально:

```text
id
side
level
entry_input_mode: PRICE | PERCENT
entry_price
entry_offset_pct
martingale_multiplier?   # только PER_ORDER_M
raw_weight
normalized_weight
planned_margin
planned_notional
configured_qty
filled_qty
remaining_entry_qty
manual_qty_lock
tp_steps                 # max 4
source
sizing_source
revision_id
validation_state
```

## 5. SideSizingConfig

Отдельная конфигурация для каждой стороны:

```text
SideSizingConfig
- side
- sizing_mode: POWER_CURVE | PER_ORDER_M
- power_k?       # POWER_CURVE
- leverage
- allocation_pct
- active_order_count
```

`PER_ORDER_M` хранит individual multipliers внутри GridOrderConfig.

## 6. StrategyLot / Filled Allocation

Появляется после первого factual fill и хранит:
- source GridOrderConfig;
- linked ExchangeOrders;
- executions;
- `filled_qty`;
- factual average entry;
- `open_qty`;
- `closed_qty`;
- realized PnL;
- TP1..TP4 state.

Factual StrategyLot не пересчитывается sizing/restructuring engine.

## 7. RestructuringPlan

```text
RestructuringPlan
- id
- scope: ORDER | GRID
- side
- trigger
- target_order_id?
- source_revision_id
- state_snapshot_id
- capital_snapshot_id
- sizing_mode
- power_k?
- effective_side_budget
- factual_used_capital
- locked_future_capital
- available_future_margin_budget
- future_notional_budget
- orders_before
- orders_after
- instrument_metadata_snapshot_id
- validation_state
- manual_review_reason?
- target_revision_id
```

Profit-taking trigger может создавать proposal, но capital routing policy Long/Short пока OPEN.

## 8. InstrumentSpec / InstrumentMetadataSnapshot

Нужно хранить актуальные exchange limits, полученные из Bybit:

```text
InstrumentSpec
- category
- symbol
- status
- min_order_qty
- qty_step
- min_notional_value
- max_order_qty
- tick_size
- fetched_at
- source_payload_hash
```

Каждый plan должен быть воспроизводимо связан со snapshot, использованным при validation.

## 9. Validation / Manual Review

Концептуальные states:

```text
VALID
BELOW_MIN_ORDER_QTY
BELOW_MIN_NOTIONAL
INVALID_QTY_STEP
INVALID_TICK_SIZE
STALE_INSTRUMENT_METADATA
INSUFFICIENT_BUDGET
RISK_DENIED
MANUAL_REVIEW
```

Если один обязательный order общего plan invalid, partial apply запрещён.

## 10. RiskDecision

```text
RiskDecision
- source_plan_id
- decision: ALLOW | MODIFY | DENY
- reasons
- modified_limits?
- created_at
```

Точная production schema остаётся FUTURE.

## 11. Execution Model

### ApprovedExecutionPlan

Утверждённый набор действий после technical validation и Risk Manager.

### ExecutionCommand

Идемпотентная команда:
- PLACE;
- AMEND;
- CANCEL;
- CLOSE.

### ExchangeOrder

Реальный order Bybit.

### Execution / Fill

Ground truth фактической сделки.

## 12. Capital / Sizing Snapshot

Для каждого sizing event хранится factual input:

```text
account fields used as capital_base candidate
long allocation
short allocation
reserve
factual used capital per side
locked future capital
available future margin budget
future notional budget
leverage
sizing mode / coefficient
instrument limits
```

Точная production formula `capital_base` остаётся OPEN.

## 13. Главная цепочка

```text
CONFIGURATION / INTENT
        ↓
SIZING
        ↓
TECHNICAL VALIDATION
        ↓
RESTRUCTURING / RISK DECISION
        ↓
APPROVED EXECUTION INTENT
        ↓
BYBIT EXCHANGE REALITY
        ↓
STRATEGY LOT / PNL / ACCOUNT STATE
```

Эти уровни нельзя схлопывать в одну сущность.
