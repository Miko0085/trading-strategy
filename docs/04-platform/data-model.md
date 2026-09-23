# Модель данных

**Статус: RECORDER РЕАЛИЗОВАН / MANUAL GRID INTENT И RESTRUCTURING MODEL ФОРМАЛИЗУЮТСЯ**

## 1. Recorder — фактическая реальность

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

## 2. Strategy Intent Model

### Grid

Долгоживущая Long или Short сетка.

### GridRevision

Immutable-версия текущего intent.

Должна содержать:
- reference market snapshot;
- allocation;
- active order count;
- GridOrderConfig;
- TP configs;
- sizing/restructuring metadata;
- before/after context.

### GridOrderConfig

Минимально:

```text
id
side
level
entry_input_mode: PRICE | PERCENT
entry_price
entry_offset_pct
martingale_multiplier
configured_qty
filled_qty
remaining_entry_qty
tp_steps
source
sizing_source
revision_id
```

В Manual Grid geometry задаёт трейдер, а future qty рассчитывает sizing layer.

### TPStepConfig

Намерение по разгрузке factual StrategyLot.

## 3. Restructuring Model

### RestructuringPlan

Предложение изменить только future intent.

Минимально:

```text
id
scope: ORDER | GRID
side
target_order_id?
source_revision_id
state_snapshot_id
effective_side_budget
factual_used_capital
locked_future_capital
available_future_budget
orders_before
orders_after
reason
validation_state
target_revision_id
```

Подтверждены два manual operation type:

```text
RECALCULATE_ORDER
RECALCULATE_GRID
```

### RestructuringEvent

Audit-факт создания/применения restructuring plan.

## 4. Risk Decision Model

```text
RiskDecision
- source_plan_id
- decision: ALLOW | MODIFY | DENY
- reasons
- modified_limits?
- created_at
```

Точная схема будет определена позже.

## 5. Execution Model

### ApprovedExecutionPlan

Утверждённый набор команд после Risk Manager.

### ExecutionCommand

Идемпотентная команда:
- PLACE;
- AMEND;
- CANCEL;
- разрешённый CLOSE.

### ExchangeOrder

Реальный order на Bybit.

### Execution / Fill

Фактическое исполнение. Это ground truth.

## 6. Position Attribution Model

### StrategyLot / Filled Allocation

Появляется после первого factual fill конкретного Grid Order и хранит:
- source GridOrderConfig;
- linked ExchangeOrders;
- executions;
- filled_qty;
- actual average entry;
- open_qty;
- closed_qty;
- realized PnL;
- TP state.

Factual StrategyLot не должен пересчитываться при volume restructuring будущих ордеров.

## 7. Capital / Sizing Snapshot

Для воспроизводимости расчёта нужна отдельная сущность/snapshot, содержащая factual inputs конкретного sizing event:

```text
capital_base / factual account fields
long allocation
short allocation
reserve
factual used capital per side
locked future capital
available future budget
leverage
instrument limits
```

Точная production-формула `capital_base` остаётся отдельным подтверждаемым правилом.

## 8. Главная цепочка

```text
INTENT
GridRevision / GridOrderConfig
        ↓
SIZING / RESTRUCTURING
RestructuringPlan
        ↓
RISK DECISION
ALLOW / MODIFY / DENY
        ↓
EXECUTION INTENT
ApprovedExecutionPlan / ExecutionCommand
        ↓
EXCHANGE REALITY
ExchangeOrder / Execution
        ↓
ATTRIBUTED RESULT
StrategyLot / PnL / Account State
```

Эти уровни нельзя схлопывать в одну сущность или считать planned qty фактическим исполнением.
