# Журнал решений

## 2026-09-18 — Внешние сигналы не используются
Стратегия не использует новости, sentiment, технические индикаторы и AI price prediction.

## 2026-09-18 — Recorder навсегда read-only
Write/trading методы не добавляются в Recorder.

## 2026-09-19 — Decision, Risk, Execution и Recorder разделены
Decision формирует action, Risk разрешает/изменяет/запрещает, Execution исполняет, Recorder фиксирует reality.

## 2026-09-19 — StrategyLot появляется после первого fill
Partial fill уже создаёт factual volume и может иметь TP.

## 2026-09-19 — Active Window является execution policy
Полная grid и активные ExchangeOrders разделены.

## 2026-09-21 — Grid Geometry, Sizing и Positioning разделены
Geometry определяет форму, Sizing — объёмы, Positioning/Trailing — положение сетки относительно рынка.

## 2026-09-21 — Allocation является постоянной policy реструктуризации
Long/Short/Reserve percentages применяются к fresh capital state при каждом restructuring, а не только при старте.

## 2026-09-21 — Future qty динамические, factual fills immutable
Новая revision может менять только будущую часть grid.

## 2026-09-21 — TP всегда factual
configured_qty не является базой закрытия. TP/close рассчитываются от filled/open qty конкретного StrategyLot.

## 2026-09-21 — Position Mode определяется per symbol
Hedge разрешает обе стороны, One-Way — только одну одновременно. Режим не переключается автоматически.

## 2026-09-21 — Risk должен быть account-level и symbol-level
Несколько grid strategies используют общий ресурс аккаунта; symbol-local проверок недостаточно.

## Правило ведения знаний
Новая прямая формулировка трейдера имеет приоритет над прежней интерпретацией. Empirical pattern не повышается до universal formula без достаточного подтверждения.
