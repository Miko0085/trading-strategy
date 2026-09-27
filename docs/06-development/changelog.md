# История изменений документации

## 2026-09-27 — полный аудит sizing / Martingale / safety

- Повторно проаудированы все разделы GitBook: overview, strategy, algorithm, risk, platform, research и development.
- Исправлены устаревшие формулировки, где qty считался вручную заданным основным параметром.
- Зафиксирован safety-first priority: сначала сохранение капитала/маржи/позиции, затем profit optimization.
- Long и Short закреплены как полностью независимые Grid с независимыми sizing settings.
- Каждый Grid Order закреплён как автономная сущность со своей Entry/TP/factual history.
- Martingale/sizing формализован через margin/notional, а не напрямую через coin qty.
- MVP сокращён до двух sizing modes: `POWER_CURVE` и advanced `PER_ORDER_M`.
- `POWER_CURVE` формализован как `raw_weight_i=(i/N)^K` с независимым `K` для Long/Short.
- `PER_ORDER_M` формализован как cumulative chain `w_i=w_(i-1)×M_i`; `M_i=1` отключает увеличение на конкретном шаге.
- Отдельные Linear/Equal/Reverse/Global-Geometric/Manual-Weights modes исключены из текущего MVP scope.
- Уточнено различие: Veles Logarithmic Distribution относится к price spacing, а наша Power Curve — к volume/notional sizing.
- Profitable TP/close повышен до подтверждённого trigger для fresh-state recalculation и restructuring proposal; routing/apply policy остаются OPEN.
- Hard Bybit minimum-lot guard закреплён как atomic invariant: любой invalid mandatory order → `MANUAL_REVIEW`, без partial apply.
- Добавлена модель InstrumentSpec / instrument metadata snapshot.
- Обновлены risk docs, Execution Engine, Bybit integration, data model, open questions и roadmap.

## 2026-09-23 — Manual Grid становится основным workflow

- Generated Grid переведён в дополнительный/legacy constructor.
- Manual Grid Geometry отделена от sizing.
- PRICE/PERCENT input подтверждён.
- Qty переведён в system-calculated future sizing.
- Factual fills закреплены immutable.
- Подтверждены `RECALCULATE_ORDER` и `RECALCULATE_GRID`.

## 2026-09-19 — архитектурная реорганизация

- Разделены Strategy Decision, Risk Manager, Execution Engine и Recorder.
- Active Order Window вынесен в execution policy.
- GridOrderConfig и ExchangeOrder получили разные lifecycle.
- StrategyLot/Filled Allocation появляется после первого fill.
- Grid Revision стала обязательным immutable audit layer.

## 2026-09-18

- Создана структура docs/.
- GitBook подключён через Git Sync.
- Зафиксирован запрет на внешние сигналы.
- Recorder и Execution Engine разделены.
