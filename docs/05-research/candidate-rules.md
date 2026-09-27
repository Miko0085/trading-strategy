# Гипотезы и возможные правила

**Статус: CANDIDATE / TRADER EXPLANATION**

Здесь остаются только правила, которые ещё не подтверждены окончательно.

## 1. Same-side reinvestment

Простой вариант:

```text
Long profitable TP  → recalculate Long future Grid
Short profitable TP → recalculate Short future Grid
```

Плюсы: причинно понятно и меньше cross-side side effects.

Статус: CANDIDATE.

## 2. Cross-side risk-priority reinvestment

После profitable TP новый capital может направляться не на ту же сторону, а туда, где он сильнее снижает risk.

Возможные факторы:
- distance Mark → LongAvg / ShortAvg;
- liquidation distance;
- margin utilization;
- available margin;
- gross exposure;
- effect on weighted average;
- reserve.

Статус: CANDIDATE.

## 3. Reinvest both sides

Новый capital может делиться между Long и Short по allocation policy.

Проблема: при небольшом capital fragmentation может привести к orders ниже Bybit minimum.

Статус: CANDIDATE.

## 4. Улучшение average через deeper re-entry

После profitable unload будущий Entry может быть расположен выгоднее:
- Long — ниже current/factual average;
- Short — выше.

Цель — улучшать average стороны и общую hedge structure.

Точная recovery/re-entry geometry пока OPEN.

## 5. Distance-to-average как один из risk factors

Если Mark ближе к average одной стороны, эта сторона может иметь больший приоритет для future capital.

Одной этой метрики недостаточно для production decision.

## 6. Positive uPnL opposite side

Положительный unrealized PnL одной стороны может учитываться как context/constraint для решения по другой стороне.

Это не равно физически доступному realized capital. Production formula пока OPEN.

## 7. Automatic TP trigger application

Profit-taking trigger уже подтверждён как повод пересчитать proposal.

Но OPEN остаётся, должен ли plan после Risk Check применяться автоматически или всегда требовать подтверждения до полной формализации routing policy.

## 8. Trailing / rebase

Pending Geometry может в будущем следовать за ценой, сохраняя factual fills неизменными.

Trigger и точная политика не подтверждены.

## 9. Short as defensive leg

**TRADER EXPLANATION:** Short рассматривается в этой стратегии прежде всего как hedge/защитная сторона и может иметь более консервативные/иные правила sizing, чем Long.

Не считать это универсальным утверждением о Short trading вне данной стратегии.
