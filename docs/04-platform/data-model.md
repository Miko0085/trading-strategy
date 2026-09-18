# Data Model

**Статус: OBSERVED FACT** — описывает уже существующую схему Recorder'а (`src/recorder/storage/`), не проектирует новую.

## Хранилища

| Слой | Назначение |
|---|---|
| JSONL (`data/raw/`) | Raw black box — точные полученные сообщения, append-only |
| SQLite WAL (`data/db/`) | Operational normalized storage |
| Parquet (`data/exports/`) | Analytical export |

## Ключевые таблицы (нормализованный слой)

- `orders`, `executions`, `positions`, `closed_pnl`, `funding` — факты по символу;
- `current_states` — последнее наблюдаемое состояние (TICKER/POSITION/WALLET/ORDER/ACCOUNT);
- `observations` — версии с `before_json`/`after_json` контекстом и provenance (`raw_id`);
- `timeline` — человекочитаемая последовательность событий;
- `trader_notes` / `trader_note_links` — объяснения трейдера и их связь с конкретными событиями timeline;
- `tracked_instruments` — реестр обнаруженных инструментов (с `stopped_at` для остановленных).

## Важные семантические ограничения (не додумывать поверх них)

- `current_states` — последнее наблюдаемое состояние, не гарантия текущей актуальности биржи.
- Изменения mark price/uPnL без изменения позиции не считаются действием трейдера (`semantic_position_change`, `src/recorder/account/positions.py`).
- Денежные значения хранятся как decimal strings, не как float — точность не теряется.
- `totalAvailableBalance` — как сообщено биржей; если поле не пришло, остаётся `NULL`, не заменяется нулём.

## Будущая Strategy Lot-модель

Таблиц для `Strategy Lot` / `take_profit_steps[]` в текущей схеме **нет** — это часть будущей platform-логики (см. [01-strategy/position-accounting.md](../01-strategy/position-accounting.md), [future-execution-engine.md](future-execution-engine.md)), не текущего Recorder'а.
