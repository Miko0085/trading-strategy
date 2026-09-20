# Базовый алгоритм исполнения сетки

**Статус: ПОДТВЕРЖДЁННЫЙ МЕХАНИЧЕСКИЙ КОНТУР**

Алгоритм исполняет заданную конфигурацию и поддерживает динамическую будущую часть сетки.

## Поток запуска

Select symbol → read factual Position Mode → validate enabled sides → read fresh account state → apply configured Long/Short/Reserve allocation → build Manual or Generated Grid → freeze Grid Geometry for current cycle → generate initial sizing → validate instrument limits → create Grid Revision → activate Active Order Window.

## Поток исполнения

ExchangeOrder → Execution/Fill → update StrategyLot → sync TP from factual open_qty → restructuring trigger → fresh account state → recalculate eligible future qty → optional trailing/repositioning → new Grid Revision → continue Active Window.

## Инварианты

- filled history immutable;
- TP/close только от factual open_qty;
- dynamic sizing меняет будущие qty, а не прошлые fills;
- allocation guard применяется при каждом перерасчёте;
- trailing не деформирует geometry текущего цикла;
- Position Mode проверяется per symbol.

## Что алгоритм не делает сам

Он не прогнозирует направление, не использует внешние сигналы, не придумывает allocation/risk limits, не переключает Bybit Position Mode и не переписывает реальные fills.
