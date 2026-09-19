# Модель данных

**Статус: RECORDER РЕАЛИЗОВАН / STRATEGY И EXECUTION MODEL ПРОЕКТИРУЮТСЯ**

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

## 2. Strategy Intent Model — что хотели сделать

Будущие сущности:

### Grid
Долгоживущая Long или Short сетка.

### GridRevision
Immutable-версия параметров Grid.

### GridOrderConfig
Логическая настройка конкретного уровня.

### TPStepConfig
Намерение по разгрузке конкретного исполненного объёма.

### RestructuringPlan
Предложение Decision Layer о том, как изменить текущую Grid. Оно ещё не означает, что действия разрешены и исполнены.

## 3. Risk Decision Model

```text
RiskDecision
- source_plan_id
- decision: ALLOW | MODIFY | DENY
- reasons
- modified_limits?
- created_at
```

Точная схема будет определена позже.

## 4. Execution Model — что отправили на биржу

### ApprovedExecutionPlan
Утверждённый набор команд после Risk Manager.

### ExecutionCommand
Отдельная идемпотентная команда: PLACE / AMEND / CANCEL / разрешённый CLOSE.

### ExchangeOrder
Реальный order на Bybit.

### Execution / Fill
Фактическое исполнение.

## 5. Position Attribution Model

### StrategyLot / Filled Allocation

Появляется после первого фактического fill конкретного Grid Order и хранит:
- source GridOrderConfig;
- linked ExchangeOrders;
- executions;
- configured_qty;
- filled_qty;
- actual average entry;
- open_qty;
- closed_qty;
- realized PnL;
- TP state.

### RestructuringEvent
Audit/research факт реструктуризации и её результата.

## Главная цепочка

```text
INTENT
GridRevision / GridOrderConfig / RestructuringPlan
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

Эти уровни нельзя схлопывать в одну таблицу или одну сущность.