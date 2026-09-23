# История изменений документации

## 2026-09-23 — Manual Grid становится основным workflow

- Generated Grid переведён в дополнительный/legacy constructor и больше не считается основным способом работы трейдера.
- Основной workflow теперь: Manual Grid Geometry → Capital Allocation → Per-Order Martingale → Automatic Future Qty → Active Order Window → Manual Volume Restructuring.
- Для Manual Grid подтверждён ввод уровня как абсолютной Entry Price либо процентного spacing.
- Подтверждён per-order Martingale: каждый multiplier умножает вес предыдущего уровня.
- Глобальный `M^i` сохранён только для optional Generated Grid.
- Подтверждено, что qty Manual Grid рассчитывает система из бюджета стороны, leverage, цены уровня и Bybit instrument limits.
- Factual fills закреплены как immutable; перераспределяться может только `remaining_entry_qty`.
- Подтверждены два manual restructuring scope: `RECALCULATE_ORDER` и `RECALCULATE_GRID`.
- Добавление нового Grid Order может сопровождаться расчётом только нового уровня либо перераспределением всей future grid.
- Обновлены Strategy Overview, Grid Mechanics, Current Algorithm, Restructuring Algorithm, Order Model, Data Model, Confirmed Rules, Open Questions, Roadmap и журнал решений.
- Полностью переписан `prototype/manual-grid-ui/IMPLEMENTATION_PROMPT.md` под новую механику.
- Обновлён README Manual Grid UI с явным разделением текущего кода и целевой подтверждённой модели.

## 2026-09-19 — архитектурная реорганизация

- Разделены Strategy Decision, Risk Manager, Execution Engine и Recorder.
- Базовый Grid Algorithm очищен от decision/risk/platform responsibilities.
- Active Order Window вынесен в отдельную execution policy.
- GridOrderConfig и ExchangeOrder получили раздельные lifecycle.
- Grid отделён от Grid Revision.
- StrategyLot/Filled Allocation теперь появляется после первого фактического fill.
- Restructuring Algorithm перестроен вокруг Capital Recalculation → Volume Recovery → Grid Restructuring → RestructuringPlan.
- Research capture реструктуризации вынесен в отдельный документ.
- Data Model расширен RestructuringPlan, RiskDecision, ApprovedExecutionPlan и ExecutionCommand.
- Roadmap разделён на Domain Model, Execution Core, Restructuring Research, Risk Manager и Controlled Automation.

## 2026-09-19 — уточнение механики после разговора с трейдером

- Исправлена прежняя интерпретация partial fill: TP считается от factual `filled_qty`.
- Зафиксировано, что несколько fills одного Grid Order остаются одной логической единицей.
- Подтверждено: обычный Take Profit является limit order.
- Подтверждён Active Order Window.
- Зафиксирована первая версия manual percentage spacing; 2026-09-23 она расширена режимом absolute price.

## 2026-09-19 — русификация

- Русский язык закреплён как основной язык публичной документации.
- Навигация GitBook переведена на русский.
- Добавлены русские определения технических терминов.
- Добавлено разделение GridOrderState / StrategyLotState / TPStepState.
- Добавлена обязательная история Grid Revision.
- Добавлена политика реакции на ручное вмешательство через терминал Bybit.

## 2026-09-18

- Создана структура docs/.
- GitBook подключён через Git Sync.
- Зафиксирован запрет на внешние сигналы.
- Разделены Recorder и Execution Engine.
