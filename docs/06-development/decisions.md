# Журнал решений

Новая прямая формулировка трейдера имеет приоритет над прежней интерпретацией. Если решение заменено, старое правило сохраняется в истории со статусом `SUPERSEDED`.

## 2026-09-18 — Внешние сигналы не используются

**STATUS: CONFIRMED**

Стратегия не использует новости, sentiment, технические индикаторы, прогнозы аналитиков или AI price prediction.

## 2026-09-18 — Recorder permanently read-only

**STATUS: CONFIRMED**

Write/trading методы не добавляются в `src/recorder/`. Execution Engine является отдельным компонентом с отдельными credentials и safety controls.

## 2026-09-19 — Grid Orders являются лимитными ордерами

**STATUS: CONFIRMED**

Entry Grid Orders и обычный TP используют лимитные заявки.

## 2026-09-19 — Первый Entry привязан к Mark Price

**STATUS: CONFIRMED**

Long #1 ниже Mark Price, Short #1 выше.

## 2026-09-19 — Percentage-only manual price mode

**STATUS: SUPERSEDED 2026-09-23**

Ранее считалось, что отдельный ввод абсолютной Entry Price не нужен. Новое решение разрешает Manual Grid задавать как ценой, так и процентным расстоянием.

## 2026-09-19 — Один Grid Order может иметь несколько fills

**STATUS: CONFIRMED**

Partial executions не создают новые логические Grid Orders.

## 2026-09-19 — TP считается от factual filled volume

**STATUS: CONFIRMED**

TP не ждёт полного configured_qty и строится от фактически исполненного объёма и factual average fill.

## 2026-09-19 — Active Order Window является execution policy

**STATUS: CONFIRMED**

Полная логическая сетка может быть больше числа ExchangeOrders, одновременно находящихся на Bybit.

## 2026-09-19 — Grid Revision обязательна

**STATUS: CONFIRMED**

Существенные изменения intent должны сохраняться как immutable revision с before/after audit.

## 2026-09-19 — Decision, Risk, Execution и Recorder разделены

**STATUS: CONFIRMED**

Decision/Planning формирует proposed action; Risk Manager проверяет; Execution Engine исполняет; Recorder фиксирует factual reality.

## 2026-09-19 — StrategyLot появляется после первого fill

**STATUS: CONFIRMED**

Factual attribution начинается после первого исполнения, а не после полного заполнения Entry.

## 2026-09-22 — Generated Grid normalized power distribution

**STATUS: CONFIRMED FOR OPTIONAL GENERATED GRID**

Формула:

```text
P_i = P1 - (P1 - PN) × ((i - 1)/(N - 1))^K
```

остаётся подтверждённой для Generated Grid, но Generated Grid больше не является primary workflow MVP.

## 2026-09-22 — Generated Grid global geometric Martingale

**STATUS: CONFIRMED FOR OPTIONAL GENERATED GRID / NOT PRIMARY MANUAL SIZING**

```text
w_i = M^(i-1)
```

остаётся валидной формулой старого Generated Grid constructor. Она не должна применяться как основная sizing-модель Manual Grid.

# Решения 2026-09-23

## Manual Grid становится основным workflow

**STATUS: CONFIRMED**

Трейдер вручную определяет Grid Geometry. Generated Grid сохраняется как дополнительный/legacy constructor и может быть скрыт из основного интерфейса.

## Manual level можно задавать Price или Percent

**STATUS: CONFIRMED**

Для каждого Grid Order поддерживается intent абсолютной Entry Price либо процентного расстояния.

## Qty в Manual Grid рассчитывает система

**STATUS: CONFIRMED**

Трейдер задаёт geometry, allocation, leverage и Martingale parameters; система рассчитывает future qty с учётом бюджета стороны и Bybit instrument limits.

## Martingale является per-order multiplier

**STATUS: CONFIRMED**

Multiplier каждого следующего уровня умножает вес предыдущего:

```text
w1 = 1
w2 = w1 × M2
w3 = w2 × M3
...
```

Это заменяет использование одного глобального `M` как основной Manual Grid sizing-модели.

## Factual fills immutable

**STATUS: CONFIRMED**

Исполненный объём не перераспределяется. Пересчитываться может только future/pending часть.

```text
configured_qty = filled_qty + remaining_entry_qty
```

## Подтверждены два manual restructuring scope

**STATUS: CONFIRMED**

```text
RECALCULATE_ORDER
RECALCULATE_GRID
```

`RECALCULATE_ORDER` изменяет future qty выбранного уровня без автоматического каскада остальных уровней.

`RECALCULATE_GRID` заново распределяет eligible future budget по всей оставшейся сетке с учётом cumulative per-order Martingale chain.

## Новый Grid Order можно добавить в активную стратегию

**STATUS: CONFIRMED**

После добавления уровня трейдер может рассчитать только новый ордер либо перераспределить future budget всей сетки.

## Manual restructuring подтверждён, automatic triggers остаются открыты

**STATUS: CONFIRMED / OPEN SPLIT**

Ручная кнопка перерасчёта входит в текущий MVP. Автоматические triggers, recovery, automatic reinvest и autonomous restructuring остаются исследовательскими вопросами.

# Решения 2026-09-26

## До четырёх Take Profit parts на Grid Order

**STATUS: CONFIRMED**

Один Grid Order / Strategy Lot использует максимум четыре TP parts (`TP1..TP4`). Доли между ними настраиваемые и не обязаны быть равными.

## Приоритет реструктуризации — безопасность всей позиции

**STATUS: CONFIRMED PRINCIPLE / ROUTING FORMULA OPEN**

Реструктуризация должна в первую очередь защищать капитал, маржу и позиции. Реинвест не обязан возвращаться в тот же Grid Order, который заработал прибыль. Основное направление исследования — пересчёт всей eligible future Grid / позиции.

## Profitable TP рассматривается как automatic restructuring trigger

**STATUS: STRONGLY SUPPORTED CANDIDATE / APPLY POLICY OPEN**

После прибыльного TP или profitable close необходимо обновить factual account state и future budget. Исследуется автоматический запуск restructuring calculation. Пока не решено, должен ли результат применяться автоматически или только формировать proposal для Risk Check / Manual Review.

## Routing reinvestment между Long и Short остаётся открытым

**STATUS: OPEN**

Зафиксированы три кандидата:

1. same-side: Long profit → Long future Grid, Short profit → Short future Grid;
2. risk-priority cross-side: капитал идёт преимущественно стороне с более высоким текущим риском/потребностью;
3. both-sides: новый капитал распределяется между обеими сторонами.

Финальная формула не подтверждена. Один из исследуемых факторов для risk-priority — расстояние Mark Price до factual average Long/Short, но одной этой метрики пока недостаточно считать правило формализованным.

## Биржевой minimum-lot guard является атомарным safety invariant

**STATUS: CONFIRMED**

Если после restructuring хотя бы один обязательный order не проходит актуальные Bybit `minOrderQty`, `qtyStep`, `minNotionalValue` или `tickSize`, новый план не применяется частично.

```text
RESTRUCTURING_PLAN_INVALID
→ MANUAL_REVIEW
→ NO PARTIAL APPLY
→ NO AUTOMATIC CONTINUE
```

Execution Engine не должен самостоятельно увеличивать qty, расходовать Reserve, пропускать невалидный уровень или менять allocation/Martingale для обхода ошибки.