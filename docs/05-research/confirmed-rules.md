# Подтверждённые правила

**Статус: ПОДТВЕРЖДЕНО**

## Grid и geometry

1. Сетка может быть ручной или автоматически сгенерированной.
2. Generated Grid задаётся количеством уровней, глубиной и коэффициентом распределения.
3. Геометрия и относительные пропорции расстояний текущего Grid Cycle сохраняются до явного rebase.
4. Active Order Window задаётся отдельно от полной logical Grid.

## Sizing и капитал

5. Qty на execution layer выражается количеством монет.
6. Initial sizing может использовать Martingale coefficient.
7. Long/Short/Reserve проценты задаются пользователем.
8. Эти проценты применяются повторно при каждом restructuring, а не только при старте.
9. Абсолютные side budgets динамичны и рассчитываются от fresh account capital state.
10. Reserve остаётся отдельной защищённой долей allocation policy.
11. Future unexecuted qty могут пересчитываться после factual/capital events.

## Fills и TP

12. Один Grid Order может иметь несколько fills.
13. После первого fill существует factual StrategyLot/Filled Allocation.
14. TP считается от factual average конкретного lot.
15. TP quantity считается от factual filled/open qty, а не от configured target.
16. Неисполненный остаток Entry не участвует в TP.
17. Ordinary TP выставляется Limit order.
18. Sum close qty не может превышать factual open_qty.
19. minOrderQty, qtyStep, minNotionalValue и tickSize проверяются per instrument.

## Position Mode

20. Position Mode определяется per symbol.
21. Hedge Mode разрешает Long only, Short only или Long+Short одновременно.
22. One-Way Mode разрешает только одну сторону одновременно.
23. enabled_long/enabled_short — отдельный Trader Intent.

## Revisions и trailing

24. Filled history immutable.
25. Dynamic qty recalculation создаёт новую Grid Revision.
26. Pending geometry может trailing-follow price при сохранении относительных пропорций.
27. Filled StrategyLots trailing не перемещает.

## Ограничения данных

28. Внешние сигналы, новости, sentiment и AI price prediction не используются.
29. Recorder остаётся read-only.
