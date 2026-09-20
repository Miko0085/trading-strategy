# Модель Long / Short

**Статус: ПОДТВЕРЖДЁННАЯ БАЗОВАЯ МЕХАНИКА**

Long и Short — независимые стороны стратегии. Они не обязаны быть симметричными по объёму, spacing, TP или allocation.

## Position Mode per symbol

Для каждого выбранного инструмента factual Position Mode читается с Bybit.

### Hedge Mode
Разрешает Long only, Short only или Long + Short одновременно.

### One-Way Mode
Разрешает Long only либо Short only. Одновременная двухсторонняя конфигурация не допускается.

### Unknown
Нельзя считать Hedge подтверждённым. Planning разрешён, но двухстороннее execution должно fail closed.

## Enabled sides

Трейдер отдельно задаёт для каждого symbol enabled_long и enabled_short. Это Trader Intent и должно сохраняться в draft/Grid Revision.

Position Mode — factual exchange state и должен запрашиваться заново.

## Capital allocation

У каждой стороны есть configured percentage бюджета, Reserve является отдельной долей. Allocation применяется не только при старте, но и при каждом restructuring event.

## Ассиметрия

Отдельные сетки не означают market-neutral hedge. Одна сторона может быть значительно больше другой.
