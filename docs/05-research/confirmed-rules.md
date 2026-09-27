# Подтверждённые правила

**Статус: CONFIRMED**

## 1. Главный приоритет — безопасность капитала

Стратегия в первую очередь должна сохранять капитал, маржу и позиции. Оптимизация прибыли вторична по отношению к контролю liquidation/margin risk.

## 2. Основной режим — Manual Grid

Generated Grid/Veles-like constructor может оставаться legacy/optional, но не определяет основной workflow.

## 3. Long и Short — независимые Grid

Они могут иметь разные:
- allocation;
- leverage;
- geometry;
- sizing mode;
- coefficients;
- active window;
- TP configuration.

## 4. Каждый Grid Order автономен

Каждый уровень имеет собственные Entry, sizing/factual fields, TP и history.

В advanced mode отдельный order может иметь свой `M_i`; `M_i=1` означает отсутствие увеличения веса на этом переходе.

## 5. Entry Geometry задаётся трейдером

Уровень можно задать:
- Price;
- Percent spacing.

Geometry и sizing независимы.

## 6. Qty рассчитывает система

Sizing использует future budget стороны, leverage, Entry Price, sizing weights и Bybit instrument limits.

Martingale применяется к margin/notional, а не напрямую к coin qty.

## 7. Для текущего функционала нужны два sizing mode

```text
POWER_CURVE
PER_ORDER_M
```

Другие modes пока не входят в MVP.

## 8. POWER_CURVE

Для eligible future orders `i=1..N`:

```text
raw_weight_i = (i/N)^K
```

`K` задаётся независимо для Long и Short. После этого веса нормализуются на future budget.

Чем выше `K`, тем больше future capital смещается к дальним levels.

## 9. PER_ORDER_M

Advanced mode:

```text
w1 = 1
w_i = w_(i-1) × M_i
```

Каждый переход между уровнями имеет собственный multiplier.

Один global geometric Martingale не нужен как отдельный mode: одинаковые `M_i` воспроизводят его.

## 10. Factual fills immutable

После исполнения factual volume нельзя перераспределять задним числом.

```text
configured_qty = filled_qty + remaining_entry_qty
configured_qty >= filled_qty
```

## 11. StrategyLot появляется после первого fill

Несколько executions одного Entry остаются одним logical Grid Order / StrategyLot attribution.

## 12. Active Order Window

Полная logical Grid может быть больше числа фактических Entry orders на Bybit.

## 13. Manual restructuring

Поддерживаются:

```text
RECALCULATE_ORDER
RECALCULATE_GRID
```

Full-grid recalculation заново распределяет eligible future budget по выбранному sizing mode.

## 14. Profit-taking event — trigger для нового расчёта

Исполнение прибыльного TP/close должно инициировать:
- fresh factual account state;
- пересчёт future budget;
- новый sizing/restructuring proposal.

Куда именно маршрутизировать капитал между Long/Short — пока OPEN.

## 15. Максимум четыре TP parts

Один Grid Order / StrategyLot использует максимум:

```text
TP1
TP2
TP3
TP4
```

Доли не обязаны быть равными.

## 16. TP считается от factual StrategyLot

TP использует factual average fill и factual open qty конкретного StrategyLot.

## 17. Биржевые limits берутся динамически из Bybit

Минимально:
- `minOrderQty`;
- `qtyStep`;
- `minNotionalValue`;
- `tickSize`;
- instrument status.

## 18. Invalid order блокирует весь соответствующий plan

Если любой обязательный order нового Execution/Restructuring Plan не проходит актуальные exchange limits:

```text
PLAN_INVALID
→ MANUAL_REVIEW
→ NO PARTIAL APPLY
```

Система не должна автоматически увеличивать qty, использовать Reserve, пропускать level или менять sizing parameters.

## 19. Grid Revision обязательна

Существенные изменения intent/sizing должны сохраняться как immutable revision с before/after audit.

## 20. External intervention требует reconciliation

Расхождение Bybit vs Platform не должно запускать скрытую стратегическую перестройку. Нужен Adopt/Restore flow.

## 21. Внешние сигналы запрещены

Не используются news, sentiment, technical indicators, analyst forecasts или AI price prediction.

## 22. Short не считается симметричным Long

**CONFIRMED AS STRATEGY DESIGN PRINCIPLE:** настройки Short не выводятся автоматически из Long. Роль Short в стратегии может быть иной, поэтому sizing/risk/TP конфигурируются независимо.
