# Исследование маршрутизации реинвеста и автоматической реструктуризации

**Статус: RESEARCH / OPEN DECISION**

Этот документ фиксирует направление исследования, чтобы не потерять логику разговора с трейдером. Он **не утверждает финальную формулу распределения капитала между Long и Short**.

## Главная цель

Приоритет стратегии — сохранить и обезопасить капитал, маржу и позиции. Реинвестирование после фиксации прибыли должно в первую очередь улучшать устойчивость стратегии, а не максимизировать размер отдельного Grid Order.

Поэтому базовая исследовательская гипотеза сейчас такая:

```text
TP / profitable close
↓
обновление factual account state
↓
обновление доступного капитала / realized PnL
↓
автоматический trigger реструктуризации
↓
пересчёт future части сетки
```

Исполненный factual volume остаётся immutable.

## Trigger

Кандидат на автоматический trigger:

- исполнение любого прибыльного Take Profit / profitable close Long;
- исполнение любого прибыльного Take Profit / profitable close Short.

После такого события система должна как минимум пересчитать доступный future budget и сформировать новый restructuring proposal.

Точная политика автоматического применения пока OPEN.

## Cross Margin и логические бюджеты

Long и Short используют один factual cross-margin account state, но это не означает, что realized profit обязан всегда перераспределяться одинаково между сторонами.

Нужно разделять:

```text
Account Cross-Margin Reality
        ↓
Strategy Capital State
        ↓
Long Future Budget
Short Future Budget
Reserve
```

Проценты базового Long / Short / Reserve allocation могут оставаться отдельной настройкой стратегии, а reinvestment routing может быть отдельным динамическим слоем.

## Кандидат A — Same-Side Reinvestment

Самый простой вариант для первого автоматического поведения:

```text
Long realized profit
→ пересчёт future Long Grid

Short realized profit
→ пересчёт future Short Grid
```

Преимущества:
- простая причинно-следственная связь;
- легко тестировать и объяснять;
- не возникает скрытого переноса капитала между сторонами;
- меньше риск непреднамеренно перегрузить противоположную сторону.

Недостаток: такая логика может быть не оптимальной для защиты позиции, если другая сторона в этот момент находится под большим риском.

Статус: CANDIDATE, не финальное правило.

## Кандидат B — Risk-Priority Cross-Side Reinvestment

Второй вариант: после каждого realized-profit trigger оценивать, какая сторона сейчас нуждается в капитале сильнее.

Один из исследуемых факторов — расстояние текущей Mark Price до factual average Long и Short:

```text
DistanceLong  = |Mark - LongAvg|
DistanceShort = |ShortAvg - Mark|
```

Если Mark Price ближе к Long average, Long может иметь более высокий приоритет для дополнительного future budget, чтобы новые более низкие Long entries могли улучшить среднюю Long и увеличить запас безопасности.

Если Mark Price ближе к Short average, зеркально приоритет может переходить к Short.

Это только кандидат. Одной дистанции до average недостаточно, чтобы считать риск формально определённым.

В будущей модели также могут понадобиться:
- distance to liquidation;
- factual used margin;
- available margin;
- side allocation utilization;
- current open qty;
- future pending exposure;
- reserve;
- эффект нового qty на новую weighted average.

Статус: CANDIDATE / NEEDS RESEARCH.

## Кандидат C — Reinvest Both Sides

Самый нейтральный вариант:

```text
new reinvestable capital
→ Long Future Grid
+ Short Future Grid
```

Капитал распределяется по обеим сторонам согласно выбранной allocation policy, после чего внутри каждой стороны перераспределяется между eligible pending orders.

Проблема: при малом realized profit дробление капитала между двумя сторонами и множеством уровней может привести к ордерам ниже минимального размера Bybit.

Статус: CANDIDATE.

## Реструктуризация должна работать на уровне всей future Grid

Текущее направление исследования: realized profit не обязан возвращаться в тот же Grid Order, который его заработал.

Более важная цель — пересчитать **всю eligible future часть стороны**, чтобы улучшать среднюю всей позиции и распределять капитал по сетке согласно sizing/risk policy.

То есть при full-grid restructuring:

```text
new side budget
- factual used capital
- locked future capital
= available future budget

→ пересчёт weights
→ новые qty всех eligible pending orders
```

Как именно выбирать сторону/стороны для нового капитала — OPEN.

## Hard Safety Gate: биржевые минимумы

Независимо от выбранной reinvestment-routing policy действует технический execution invariant:

> Если после реструктуризации хотя бы один ордер, который должен войти в новый Execution Plan, не проходит актуальные Bybit instrument limits, вся реструктуризация не должна применяться частично.

Проверяются как минимум:
- `minOrderQty`;
- `qtyStep`;
- `minNotionalValue`;
- `tickSize` для цены.

Если любой обязательный ордер после нормализации остаётся ниже биржевого минимума или технически невалиден:

```text
RESTRUCTURING_PLAN_INVALID
↓
MANUAL_REVIEW
↓
NO PARTIAL APPLY
↓
NO AUTOMATIC CONTINUE
```

Нельзя допустить состояние, где часть новой сетки выставилась, а другая часть не выставилась только потому, что ей не хватило минимального lot/notional.

Execution Engine не должен самостоятельно:
- увеличивать qty до биржевого минимума за счёт Reserve;
- переносить недостающий капитал с другой стороны;
- пропускать невалидный уровень и продолжать остальные;
- менять Martingale или allocation, чтобы "починить" план.

Такие изменения требуют нового планирования или manual review.

## Источник instrument limits

Актуальные ограничения инструмента должны загружаться из Bybit V5 Instruments Info и храниться в локальном instrument metadata cache/snapshot.

Перед будущим реальным PLACE / AMEND Execution Engine обязан использовать свежую спецификацию инструмента и валидировать план до отправки команд на биржу.

## Что нужно исследовать дальше

1. Какая routing policy является базовой: same-side, cross-side risk priority или обе стороны одновременно?
2. Если нужен cross-side routing, какая точная формула определяет приоритет стороны?
3. Достаточно ли расстояния Mark Price до LongAvg/ShortAvg, или обязательны liquidation/margin metrics?
4. Сохраняется ли базовый Long/Short allocation при reinvestment или допускается временное динамическое отклонение?
5. Что именно реинвестируется: только net realized profit или весь released capital + profit?
6. Какой минимальный размер reinvestment нужен, чтобы не дробить капитал на неисполняемые ордера?
7. Что происходит, если valid restructuring возможно только для одной стороны?
8. Должен ли автоматический TP trigger только формировать proposal или сразу применять его после Risk Check?

До отдельного подтверждения трейдера эти пункты нельзя повышать до CONFIRMED RULE.