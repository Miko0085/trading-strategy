# Модель Long / Short

**Статус: ПОДТВЕРЖДЁННАЯ АВТОНОМНОСТЬ СТОРОН / ROUTING CAPITAL OPEN**

Стратегия работает в Hedge Mode: Long и Short по одному инструменту могут существовать одновременно.

## Long и Short — не зеркальные копии

Это две автономные Grid:
- Long Grid;
- Short Grid.

У каждой стороны могут быть собственные:
- allocation;
- leverage;
- Entry geometry;
- sizing mode;
- Power Curve coefficient `K`;
- per-order `M_i`;
- Active Order Window;
- TP1..TP4;
- risk limits;
- factual position history.

Нельзя автоматически переносить параметры Long на Short или наоборот.

## Автономность Grid Orders

Каждый Grid Order внутри стороны — отдельная сущность.

Например:
- Long #4 может иметь `M=1.00`, то есть без увеличения веса;
- Short #4 может иметь существенно больший `M`;
- разные уровни могут иметь разные TP и factual average fill.

## Базовая геометрия

- первый Long Entry располагается ниже reference Mark Price;
- первый Short Entry — выше;
- следующие Entry задаются вручную ценой или процентным spacing.

## Sizing

Подтверждены два необходимых sizing mode:

### POWER_CURVE

Один side-level коэффициент `K` автоматически задаёт форму распределения future notional между уровнями.

### PER_ORDER_M

Advanced mode: каждый переход уровня имеет собственный multiplier `M_i`.

Global geometric с одним `M` не нужен как отдельный режим: если всем `M_i` задать одинаковое значение, получается тот же результат.

## Объяснение трейдера о роли сторон

**TRADER EXPLANATION:** Long и Short имеют разную экономическую роль внутри стратегии. Short рассматривается прежде всего как hedge/защитная сторона, поэтому его sizing и удержание не должны автоматически считаться симметричными Long.

Это объяснение нельзя превращать в универсальное утверждение о прибыльности Short на рынке вообще; оно относится к данной стратегии.

## Cross Margin

Обе стороны используют factual состояние одного cross-margin аккаунта, но логические future budgets Long и Short должны учитываться отдельно.

## Что пока OPEN

- точная production-формула `capital_base`;
- базовые проценты Long/Short/Reserve;
- когда realized profit остаётся на той же стороне;
- когда допускается cross-side reinvestment;
- какая risk metric определяет приоритет стороны;
- допускается ли временное отклонение от базового allocation;
- точные liquidation/risk thresholds.
