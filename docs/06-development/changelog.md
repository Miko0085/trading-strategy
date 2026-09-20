# История изменений документации

## 2026-09-21 — динамическая сетка и эмпирическая валидация

- Grid Geometry, Grid Sizing и Grid Positioning/Trailing разделены как независимые механизмы.
- Добавлен Generated Grid: N, depth, first offset и distribution coefficient.
- Добавлен initial Martingale sizing как отдельный от geometry механизм.
- Зафиксировано: относительные пропорции geometry текущего цикла сохраняются.
- Зафиксировано: future unexecuted qty динамически пересчитываются.
- Long/Short/Reserve allocation теперь применяется на каждом restructuring event.
- Position Mode описан per symbol: Hedge / One-Way / Unknown.
- TP/close для крупных partial fills рассчитывается только от factual filled/open qty.
- Усилены instrument constraints: qtyStep, minOrderQty, minNotionalValue, tickSize.
- Trailing описан как перенос pending geometry без изменения filled StrategyLots.
- Добавлен исследовательский документ по фактической торговле 13–20 сентября 2026.
- LSKUSDT зафиксирован как наиболее полная выборка периода.
- Паттерны около +9–12% / около половины lot оставлены сильной гипотезой, а не универсальным правилом.
- Tail-risk и account-level risk усилены фактическим liquidation наблюдением.

## 2026-09-19 — архитектурная реорганизация

- Разделены Strategy Decision, Risk Manager, Execution Engine и Recorder.
- Active Order Window вынесен в execution policy.
- GridOrderConfig и ExchangeOrder получили раздельные lifecycle.
- StrategyLot/Filled Allocation появляется после первого фактического fill.
- Restructuring Algorithm формирует RestructuringPlan.

## 2026-09-18

- Создана структура docs/.
- GitBook подключён через Git Sync.
- Зафиксирован запрет на внешние сигналы.
- Разделены Recorder и Execution Engine.
