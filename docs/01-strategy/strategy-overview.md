# Обзор стратегии

**Статус: ПОДТВЕРЖДЁННАЯ МЕХАНИКА + ОТКРЫТЫЕ ТОЧНЫЕ ФОРМУЛЫ**

Стратегия — динамическая grid-система управления Long/Short inventory. Она не требует закрывать всю агрегированную позицию для фиксации результата: отдельные Strategy Lots могут частично разгружаться и снова набираться, пока остальная позиция продолжает существовать.

## Шесть независимых механизмов

1. Position Mode — что разрешает Bybit для выбранного symbol.
2. Grid Geometry — где находятся уровни и каковы пропорции расстояний.
3. Grid Positioning / Trailing — где вся неисполненная geometry находится относительно рынка.
4. Grid Sizing / Capital Allocation — каким объёмом заполняется каждый будущий уровень.
5. Lot Management / Execution — что реально исполнилось и сколько фактически можно разгружать.
6. Restructuring — как после событий пересчитать будущую часть сетки.

Эти механизмы нельзя смешивать: изменение объёма не обязано менять расстояния; trailing не должен переписывать фактические fills; агрегированная позиция Bybit не заменяет учёт Strategy Lots.

## Position Mode и стороны стратегии

Position Mode определяется по Bybit отдельно для выбранного инструмента.

- Hedge Mode: разрешён Long only, Short only или Long + Short одновременно.
- One-Way Mode: разрешена только одна сторона одновременно.
- Unknown: режим нельзя считать подтверждённым.

Трейдер отдельно включает Long и Short для каждого symbol. Hedge Mode разрешает двухстороннюю торговлю, но не требует её.

## Создание сетки

Сетка может быть Manual Grid или Generated Grid. Generated Grid строится по количеству уровней, глубине, первому отступу, коэффициенту распределения, initial sizing, Martingale coefficient и Active Order Window.

После генерации оба режима приводятся к обычным GridOrderConfig.

## Основная динамика

Base Grid → Active Window → fills → Strategy Lots → TP/partial close → restructuring trigger → fresh account capital → Long/Short/Reserve allocation → recalculation future qty + optional trailing → new Grid Revision.

## Что подтверждено

- геометрия текущего Grid Cycle и пропорции расстояний сохраняются до явного rebase;
- абсолютные объёмы будущих неисполненных уровней могут меняться;
- Long/Short/Reserve проценты являются постоянной policy текущей конфигурации и применяются при каждом перерасчёте;
- TP и разгрузка рассчитываются от фактически исполненного/open объёма;
- partial fill является нормальным состоянием;
- already-filled history не переписывается новой revision;
- pending grid может перемещаться за ценой при сохранении geometry;
- внешние новости, sentiment, индикаторы и AI-прогноз направления не используются.

## Что ещё не формализовано

- точная математическая функция распределения уровней;
- точная dynamic sizing formula;
- trailing trigger и step;
- recovery qty и price;
- funding/fees treatment;
- TP rounding/residual;
- rolling partial-fill TP synchronization;
- точные пороги будущего Risk Manager.
