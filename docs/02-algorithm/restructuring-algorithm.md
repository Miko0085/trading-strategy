# Алгоритм реструктуризации сетки

**Статус: MANUAL VOLUME RESTRUCTURING CONFIRMED / AUTOMATIC TRIGGERS OPEN**

Реструктуризация — отдельный planning layer. Она не должна напрямую отправлять команды на Bybit.

На текущем этапе подтверждена ручная реструктуризация объёма, запускаемая трейдером из интерфейса.

## Главный invariant

```text
Factual filled/open volume → immutable
Future/pending volume      → может пересчитываться
```

Нельзя уменьшать или перераспределять уже исполненный объём так, будто сделки не было.

## Входы

Используются только объективные данные стратегии и аккаунта:
- current Mark Price;
- Long / Short factual position;
- StrategyLots;
- filled_qty / open_qty;
- average fill;
- available margin / capital snapshot;
- current allocation;
- pending Grid Orders;
- per-order Martingale multipliers;
- leverage;
- Bybit instrument limits;
- current Grid Revision.

Внешние новости, sentiment, индикаторы и прогнозы не используются.

## Подтверждённые manual triggers

### 1. RECALCULATE_ORDER

Трейдер выбирает конкретный Grid Order и запускает перерасчёт его future qty.

Правила:
- factual `filled_qty` не меняется;
- `open_qty` не меняется этим действием;
- остальные уровни не должны автоматически пересчитываться;
- новый remaining qty должен помещаться в доступный future budget;
- применяются актуальные leverage и instrument limits;
- результат создаёт новую Grid Revision.

Это точечный перерасчёт, а не каскадирование Martingale chain по всей сетке.

### 2. RECALCULATE_GRID

Трейдер запускает перерасчёт всей future части Long или Short.

Поток:

```text
Fresh factual account state
↓
Current Side Budget
↓
Subtract Factual Used Capital
↓
Subtract Locked Future Capital
↓
Available Future Budget
↓
Build cumulative per-order Martingale weights
↓
Normalize weights across eligible pending levels
↓
Recalculate remaining_entry_qty
↓
Validate Bybit limits
↓
RestructuringPlan
↓
Grid Revision
```

## Per-Order Martingale Chain

Для всей сетки веса считаются последовательно:

```text
w1 = 1
w2 = w1 × M2
w3 = w2 × M3
...
wn = w(n-1) × Mn
```

После этого веса eligible future levels нормализуются на доступный future budget.

Изменение `M` одного уровня влияет на него и потенциально на последующие веса только при `RECALCULATE_GRID`.

При `RECALCULATE_ORDER` изменения не должны автоматически каскадировать на остальные уровни.

## Добавление новых уровней

Если трейдер добавил новый ордер в существующую сетку, доступны два действия:

```text
Calculate only this new order
или
Recalculate entire future grid
```

Второй вариант включает новый уровень в общую Martingale chain и перераспределяет eligible future budget.

## Factual Used Capital

До перераспределения система должна учесть капитал, уже занятый фактически открытым объёмом стратегии.

Концептуально:

```text
AvailableFutureBudget
= EffectiveSideBudget
- FactualUsedCapital
- LockedFutureCapital
```

Точная production-семантика `EffectiveSideBudget`/`capital_base` должна быть подтверждена отдельно, чтобы не допустить двойного учёта equity/PnL.

## Выход: RestructuringPlan

Минимально:

```text
RestructuringPlan
- scope: ORDER | GRID
- target_order_id?
- side
- source_revision
- factual_state_snapshot
- effective_side_budget
- factual_used_capital
- locked_future_capital
- available_future_budget
- orders_before
- orders_after
- validation
- reason
- target_grid_revision
```

## Дальнейший pipeline

```text
Current State
↓
Manual Restructuring Request
↓
RestructuringPlan
↓
Risk Manager
↓
ALLOW / MODIFY / DENY
↓
ApprovedExecutionPlan
↓
Execution Engine
↓
Bybit
```

В shadow/read-only MVP результат остаётся virtual и не отправляется на биржу.

## Что подтверждено

- ручной перерасчёт одного future order;
- ручной перерасчёт всей future grid;
- factual fills immutable;
- future qty может изменяться;
- добавление новых уровней может сопровождаться перерасчётом;
- per-order Martingale chain используется при полном перерасчёте;
- restructuring создаёт новую Grid Revision;
- geometry не должна автоматически меняться только из-за sizing recalculation.

## Что остаётся OPEN

- automatic restructuring triggers;
- automatic reinvest triggers;
- automatic volume recovery после TP;
- точная production-формула capital_base;
- автоматический rebase;
- trailing trigger policy;
- autonomous decision rules;
- Risk Manager limits.
