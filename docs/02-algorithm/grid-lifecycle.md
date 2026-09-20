# Жизненный цикл Grid

**Статус: БАЗОВАЯ ДОМЕННАЯ МОДЕЛЬ**

Grid — долгоживущая сущность стратегии для конкретного symbol и side.

## Grid Cycle

Внутри Grid существует цикл с собственной geometry и anchor. Grid Cycle фиксирует geometry, reference/anchor, sizing policy, allocation policy, enabled side и revisions.

## Grid Revision

Любое существенное изменение будущей конфигурации создаёт immutable revision. Причины: dynamic qty recalculation, trailing/rebase, manual parameter edit, изменение allocation, Active Window или TP configuration.

Revision не меняет прошлую exchange reality.

Пример: Revision #1 initial → Revision #2 qty recalculation → Revision #3 trailing.

Новый Geometry Cycle нужен, когда явно заменяется geometry, а не просто двигается её anchor.
