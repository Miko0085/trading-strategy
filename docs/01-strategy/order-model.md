# Order Model

**Статус: OBSERVED FACT (Bybit-семантика) / FUTURE (внутренний lot-учёт)**

## Bybit truth (уже реализовано в Recorder)

- `execution` = факт фактического исполнения. Это не то же самое, что статус ордера.
- `order lifecycle != execution`. Нельзя считать сделку исполненной только потому, что order-событие показывает `Filled`.
- Один order может иметь несколько executions (частичные исполнения).
- Execution должен иметь собственную identity/дедупликацию (`execId` у Bybit).
- Raw payload сохраняется до нормализации (см. [04-platform/bybit-integration.md](../04-platform/bybit-integration.md)).

Это уже реализовано в Recorder'е (`src/recorder/events/ingestion.py`, `src/recorder/storage/`) и не переписывается.

## Редактирование параметров (FUTURE)

Каждый Grid Order и Strategy Lot должен быть конфигурируемым:

- spacing;
- qty;
- TP levels;
- partial close percentage;
- active/cancel state.

Изменения должны быть **audit-able**: before / after / timestamp / order-или-lot / reason-comment (если есть). Это будущая функциональность внутренней платформы (не Recorder), см. [04-platform/future-execution-engine.md](../04-platform/future-execution-engine.md).
