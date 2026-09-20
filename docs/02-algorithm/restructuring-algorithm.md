# Алгоритм реструктуризации сетки

**Статус: ПОДТВЕРЖДЁН КОНТУР / ОТКРЫТЫ ТОЧНЫЕ ФОРМУЛЫ**

Реструктуризация — event-driven decision layer. Она не отправляет сделки напрямую на Bybit.

## Главный принцип

Реструктуризация сохраняет factual history и меняет только будущую часть стратегии.

## Triggers

К классу triggers относятся события, изменяющие factual state или капитал сетки: Entry partial/full fill, TP partial/full fill, partial/full close, изменение доступного капитала, manual capital addition/withdrawal. Конкретная debounce/coalescing policy определяется при реализации.

## Capital Recalculation

При каждом restructuring используется fresh account state. Настроенные Long allocation %, Short allocation % и Reserve % применяются заново к актуальной капиталовой базе.

Процент фиксирован до изменения настройки трейдером. Абсолютная сумма динамична. Reserve нельзя автоматически потреблять для расширения Long/Short сверх заданной policy.

## Dynamic Sizing

После расчёта текущего side budget пересчитываются только eligible future quantities.

- filled history — immutable;
- open factual lot — factual;
- future pending/queued qty — recalculable.

Grid Geometry при обычном sizing recalculation сохраняется.

## Volume Recovery

Фактическая торговая практика показывает повторный набор объёма после предыдущих разгрузок и нового движения цены. Подтверждён феномен recovery/reload inventory; открыты exact qty, связь с конкретным sold lot, recovery distance и использование realized profit.

## Grid Positioning / Trailing

Trailing — отдельный блок реструктуризации. Он меняет anchor и цены неисполненной сетки при сохранении geometry proportions. Filled StrategyLots не перемещаются.

Открыты trigger, step, continuous/discrete behavior и policy для уже выставленных pending ExchangeOrders.

## Выход

Current State → Restructuring Algorithm → RestructuringPlan → Risk Manager → ALLOW/MODIFY/DENY → ApprovedExecutionPlan → Execution Engine → Bybit.

RestructuringPlan должен содержать trigger, capital/allocation snapshot, geometry reference, qty changes, keep/cancel/amend/create actions, optional new anchor и target Grid Revision.

## Что ещё нельзя додумывать

Exact dynamic sizing formula, distribution formula, recovery formula, trailing trigger, funding/fees treatment и risk thresholds.
