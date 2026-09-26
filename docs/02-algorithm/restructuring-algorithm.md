# Алгоритм реструктуризации сетки

**Статус: MANUAL VOLUME RESTRUCTURING CONFIRMED / AUTOMATIC REINVESTMENT ROUTING OPEN**

Реструктуризация — отдельный planning layer. Она не должна напрямую отправлять команды на Bybit.

На текущем этапе подтверждена ручная реструктуризация объёма, запускаемая трейдером из интерфейса. Автоматическая реструктуризация после фиксации прибыли исследуется отдельно и пока не имеет финальной routing formula.

## Главный invariant

```text
Factual filled/open volume → immutable
Future/pending volume      → может пересчитываться
```

Нельзя уменьшать или перераспределять уже исполненный объём так, будто сделки не было.

## Приоритет стратегии

Первый приоритет реструктуризации — сохранение и защита капитала, маржи и позиций. Увеличение объёма или доходности отдельного Grid Order не должно иметь приоритет над безопасностью всей позиции.

Поэтому основное направление исследования — full-grid / portfolio-level restructuring, а не обязательное возвращение прибыли в тот же Grid Order, который её заработал.

## Входы

Используются только объективные данные стратегии и аккаунта:
- current Mark Price;
- Long / Short factual position;
- Long / Short factual average;
- StrategyLots;
- filled_qty / open_qty;
- average fill;
- realized PnL;
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

## Исследуемый automatic trigger: profitable close / Take Profit

Новое направление исследования:

```text
Profitable TP / profitable close
↓
refresh factual account state
↓
refresh realized PnL / available capital
↓
automatic restructuring trigger
↓
recalculate future budget
↓
select reinvestment routing policy
↓
new RestructuringPlan
```

Пока **не подтверждено**, должен ли такой trigger автоматически применять новый plan или только формировать proposal для Risk Check / Manual Review.

## Маршрутизация нового капитала между Long и Short — OPEN

Long и Short используют общий factual cross-margin account state, но логические бюджеты стратегии могут перераспределяться по отдельным правилам.

Сейчас рассматриваются три кандидата:

### A. Same-Side Reinvestment

```text
Long realized profit  → пересчёт future Long Grid
Short realized profit → пересчёт future Short Grid
```

Это самый простой и предсказуемый вариант, но он может быть не оптимальным, если противоположная сторона в моменте более уязвима.

### B. Risk-Priority Cross-Side Reinvestment

После trigger система оценивает, какая сторона требует большего усиления с точки зрения сохранения позиции.

Один из кандидатов-факторов — расстояние Mark Price до factual average Long / Short. Если текущая цена ближе к средней одной стороны, эта сторона может получить больший приоритет для future budget, чтобы будущие входы улучшали её среднюю и запас безопасности.

Одной дистанции до average пока недостаточно для финального правила. Возможно понадобятся также liquidation distance, factual used margin, allocation utilization, reserve, pending exposure и эффект нового qty на weighted average.

### C. Reinvest Both Sides

Новый доступный капитал распределяется сразу между Long и Short согласно выбранной allocation policy, а затем внутри каждой стороны — по eligible pending orders.

Проблема этого варианта: при малой сумме realized profit дробление капитала может привести к ордерам ниже минимального lot/notional Bybit.

Подробно кандидаты зафиксированы в `docs/05-research/reinvestment-routing-research.md`.

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

## Hard Safety Gate: minimum lot / notional

Независимо от manual или будущего automatic trigger, любой новый RestructuringPlan должен пройти атомарную техническую проверку instrument limits.

Минимум:
- `minOrderQty`;
- `qtyStep`;
- `minNotionalValue`;
- `tickSize`.

Если после нормализации **хотя бы один обязательный ордер нового плана** не проходит актуальные Bybit limits:

```text
RESTRUCTURING_PLAN_INVALID
↓
MANUAL_REVIEW
↓
NO PARTIAL APPLY
↓
NO AUTOMATIC CONTINUE
```

Нельзя допускать частичное применение реструктуризации, при котором одни уровни выставились, а другие были отвергнуты биржей из-за минимального lot/notional.

Execution Engine не имеет права самостоятельно:
- увеличивать qty до минимума за счёт Reserve;
- переносить капитал с другой стороны;
- пропускать невалидный уровень и продолжать остальные;
- менять allocation или Martingale для обхода ошибки.

Для исправления нужен новый planning calculation либо manual review.

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
- reinvestment_trigger?
- reinvestment_source_side?
- proposed_target_side_allocation?
- orders_before
- orders_after
- instrument_limits_snapshot
- validation
- reason
- target_grid_revision
```

## Дальнейший pipeline

```text
Current State
↓
Manual Request or Future Automatic Trigger
↓
RestructuringPlan
↓
Hard Instrument Validation
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
- geometry не должна автоматически меняться только из-за sizing recalculation;
- невалидный по биржевым минимумам restructuring plan не должен частично применяться и должен уходить в Manual Review.

## Что остаётся OPEN

- финальная automatic trigger policy после TP/profitable close;
- same-side vs cross-side vs both-sides reinvestment routing;
- формула приоритета Long/Short при cross-side routing;
- что именно реинвестируется: net realized profit или released capital + profit;
- точная production-формула capital_base;
- automatic volume recovery после TP;
- автоматический rebase;
- trailing trigger policy;
- autonomous decision rules;
- Risk Manager limits.