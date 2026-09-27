# Журнал решений

Новая прямая формулировка трейдера имеет приоритет над прежней интерпретацией. Заменённые решения сохраняются как `SUPERSEDED`.

## 2026-09-18 — Внешние сигналы не используются

**STATUS: CONFIRMED**

Новости, sentiment, technical indicators и AI price prediction не участвуют в стратегии.

## 2026-09-18 — Recorder permanently read-only

**STATUS: CONFIRMED**

Trading write path существует только в отдельном Execution Engine.

## 2026-09-19 — Grid Orders и TP являются limit orders

**STATUS: CONFIRMED**

Обычный Entry и обычный Take Profit используют limit orders.

## 2026-09-19 — Первый Entry привязан к Mark Price

**STATUS: CONFIRMED**

Long #1 ниже Mark, Short #1 выше.

## 2026-09-19 — Percentage-only Entry

**STATUS: SUPERSEDED 2026-09-23**

Manual Grid теперь поддерживает PRICE и PERCENT.

## 2026-09-19 — Partial fills

**STATUS: CONFIRMED**

Один Grid Order может иметь несколько executions. StrategyLot появляется после первого fill.

## 2026-09-19 — Active Order Window

**STATUS: CONFIRMED**

Полная Grid может быть больше числа фактических ExchangeOrders на Bybit.

## 2026-09-19 — Grid Revision / layer separation

**STATUS: CONFIRMED**

Strategy/Decision, Risk, Execution и Recorder разделены. Существенные изменения intent сохраняются immutable revision.

## 2026-09-22 — Generated Grid formulas

**STATUS: LEGACY / OPTIONAL**

Veles-like Generated Grid power price distribution и global geometric sizing могут оставаться в legacy code/research, но не определяют primary Manual Grid UI.

# Решения 2026-09-23

## Manual Grid — primary workflow

**STATUS: CONFIRMED**

Трейдер вручную задаёт Geometry; qty рассчитывает система.

## Factual fills immutable

**STATUS: CONFIRMED**

Пересчитывается только future/pending volume.

## Manual restructuring

**STATUS: CONFIRMED**

Поддерживаются `RECALCULATE_ORDER` и `RECALCULATE_GRID`.

# Решения 2026-09-26

## Максимум четыре TP parts

**STATUS: CONFIRMED**

Один Grid Order / StrategyLot использует максимум TP1..TP4. Доли настраиваются и не обязаны быть равными.

## Приоритет реструктуризации — безопасность всей позиции

**STATUS: CONFIRMED PRINCIPLE**

Сохранение капитала, маржи и позиций имеет приоритет над максимизацией прибыли.

## Reinvestment не обязан возвращаться в заработавший Grid Order

**STATUS: CONFIRMED DIRECTION / ROUTING OPEN**

Основное направление — full-grid recalculation future части стороны/позиции.

## Atomic minimum-lot guard

**STATUS: CONFIRMED**

Если любой обязательный order нового plan не проходит актуальные Bybit limits, весь plan блокируется:

```text
PLAN_INVALID
→ MANUAL_REVIEW
→ NO PARTIAL APPLY
```

# Решения 2026-09-27

## Long и Short полностью автономны

**STATUS: CONFIRMED**

Стороны не считаются симметричными. У каждой собственные allocation, leverage, Geometry, sizing mode, coefficients, Active Window и TP.

Каждый Grid Order также автономен и имеет собственный factual state/history.

## Sizing считается через margin/notional, а не напрямую через qty

**STATUS: CONFIRMED**

Canonical pipeline:

```text
Future Margin Budget
× leverage
= Future Notional Budget
→ sizing weights
→ notional_i
→ qty_i = notional_i / entry_price_i
→ Bybit normalization
```

## MVP оставляет только два sizing mode

**STATUS: CONFIRMED FUNCTIONAL SCOPE**

```text
POWER_CURVE
PER_ORDER_M
```

Отдельные `LINEAR`, `EQUAL`, `REVERSE_GEOMETRIC`, `MANUAL_WEIGHTS` и `GLOBAL_GEOMETRIC` не добавляются как самостоятельные MVP modes.

## POWER_CURVE

**STATUS: CONFIRMED FOR FUNCTIONAL IMPLEMENTATION**

Для `N` eligible future orders:

```text
raw_weight_i = (i/N)^K
```

После normalization веса распределяют future budget. `K` задаётся независимо для Long и Short.

Название `Power Curve / Степенное распределение` используется вместо «логарифмический мартингейл», потому что формула степенная.

Veles `Logarithmic Distribution` относится к price spacing; в нашей платформе Power Curve применяется к sizing weights, поэтому Geometry и Sizing разделены.

## PER_ORDER_M

**STATUS: CONFIRMED ADVANCED MODE**

```text
w1 = 1
w_i = w_(i-1) × M_i
```

Каждый переход имеет собственный multiplier. `M_i=1` означает отсутствие увеличения на этом шаге.

Если все `M_i` одинаковы, получается обычный global geometric Martingale, поэтому отдельный global mode не нужен.

## Profitable TP/close — restructuring calculation trigger

**STATUS: CONFIRMED TRIGGER / APPLY POLICY OPEN**

После прибыльного TP/close обязательно:

```text
fresh factual account state
→ recalculate future budget
→ new sizing/restructuring proposal
```

Пока OPEN:
- что именно считается reinvestable capital;
- same-side / cross-side / both-side routing;
- automatic apply after Risk Check.

## Short role

**STATUS: TRADER EXPLANATION**

В рамках этой стратегии Short рассматривается прежде всего как hedge/защитная сторона и поэтому может иметь существенно иной sizing profile, чем Long. Это не универсальное утверждение о Short trading вне стратегии.
