# DEVELOPMENT RULES — BYBIT STRATEGY RECORDER

> Перед изменением логики стратегии/платформы сначала прочитайте `docs/README.md` и:
> `docs/00-overview/principles.md`, `docs/01-strategy/strategy-overview.md`, `docs/02-algorithm/current-algorithm.md`, `docs/05-research/confirmed-rules.md`, `docs/05-research/open-questions.md`, `docs/06-development/decisions.md`.

## 1. Scope

Текущий scope — read-only Strategy Recorder.

Любая новая задача сначала проверяется на соответствие текущему этапу. Если она преждевременно превращает Recorder в Strategy Engine или Trading Bot — не реализовывать без отдельного явного решения.

## 2. Bybit

- Использовать актуальную официальную Bybit V5 документацию.
- Не придумывать endpoints и fields.
- Не использовать устаревшие V2/V3 примеры как источник истины.
- Public и Private WebSocket рассматривать как realtime event sources.
- REST использовать для reconciliation, recovery, history и backfill.
- Сохранять raw payload до нормализации.
- Учитывать reconnect, partial executions и duplicate/repeated events.

## 3. Read-only

В проекте не должно быть торговых методов и вызовов:
- place order;
- amend order;
- cancel order;
- close position;
- set leverage;
- set TP/SL.

Private collector должен работать только с read-only API key.

Secrets не логировать и не хранить в Git.

## 4. Data integrity

Главный приоритет — полнота и воспроизводимость dataset.

- RAW не удалять из-за deduplication.
- Deduplication выполнять на normalized layer.
- Execution считать фактом фактического исполнения.
- Order status Filled не превращать автоматически в trade.
- Один order может иметь несколько executions.
- Все reconciliation decisions должны быть audit-friendly.
- Data gaps фиксировать явно.

### Удаление связей пояснение → событие

- Запрещено удалять существующие связи без явного подтверждения трейдера. Правило действует для Telegram, CLI, AI-разработчика, миграций и автоматических исправлений.
- До подтверждения показать ID пояснения и конкретные события, связи с которыми будут удалены. Замена события также считается удалением прежней связи.
- Снятие отметки, выбор другого события, пустой список и обычная кнопка «Сохранить выбранные связи» сами по себе не являются подтверждением удаления. Это только подготовка изменения.
- Требуется отдельное действие с однозначным смыслом: «Подтвердить удаление перечисленных связей». При отмене или отсутствии подтверждения сохранять прежние связи, контекст и статус подтверждения заметки.
- Подтверждение относится только к показанному набору изменений и актуальной ревизии пояснения. Устаревшие подтверждения не применять; нельзя подтверждать за другого пользователя.
- После подтверждённого удаления атомарно обновить связи и контекст, сохранить предыдущую версию в истории и сбросить подтверждение пояснения до повторной проверки трейдером. Исходный текст, аудио и историю не удалять.
- Тесты не должны удалять реальные связи ради проверки без отдельного подтверждения; использовать изолированную тестовую БД.

## 5. Storage

Использовать:
- JSONL — raw black box;
- SQLite WAL — operational normalized storage;
- Parquet — analytical export.

Collectors не должны быть жёстко связаны с конкретной реализацией SQLite. Использовать repository/storage boundaries, чтобы позже можно было перейти на PostgreSQL.

## 6. Event ingestion

Предпочтительный поток:

```text
SOURCE
↓
RAW WRITE
↓
ASYNC QUEUE
↓
NORMALIZATION
↓
CONTROLLED SQLITE WRITER
↓
TIMELINE / INTERPRETER
```

Не выполнять длинные независимые SQLite transactions непосредственно из каждого WebSocket callback.

## 7. Failure isolation

- Telegram failure не останавливает Bybit collector.
- STT failure не приводит к потере voice.
- Normalization failure не приводит к потере raw payload.
- Export failure не уничтожает SQLite/JSONL.
- Reconciliation failure фиксируется явно.
- Graceful shutdown должен drain pending writes.

## 8. Configuration

Не hardcode:
- symbols;
- candle intervals;
- ticker sampling;
- optional market streams;
- reconciliation intervals;
- Telegram notification policy;
- event-linking windows.

Использовать YAML + ENV.

Secrets — только ENV.

## 9. Trader UX

Весь пользовательский интерфейс трейдера — на русском языке.

Telegram не должен спамить raw WebSocket events.

Технические события агрегируются в human-level события, но underlying events не теряются.

Трейдер должен иметь возможность:
- увидеть текущее состояние;
- увидеть последние действия;
- выбрать действие;
- пояснить текстом;
- пояснить голосом;
- проверить транскрипцию;
- подтвердить или исправить event links.

## 10. Voice

Всегда хранить отдельно:
- original audio;
- verbatim transcript;
- AI interpretation (если появится позже).

AI summary никогда не заменяет оригинальную транскрипцию.

Если STT недоступен — сохранять voice и статус pending/failed с возможностью повторной обработки.

## 11. Strategy knowledge

Никогда не додумывать торговые правила.

Использовать три уровня:

1. Observed Fact
2. Trader Explanation
3. Confirmed Rule

Пример трейдера не является правилом.

При противоречии между объяснениями — зафиксировать ambiguity и запросить подтверждение.

## 12. Coding principles

- Python 3.12+.
- Async I/O там, где это оправдано.
- Небольшие модули с понятной ответственностью.
- Type hints.
- Structured logging.
- Explicit error handling.
- Idempotent ingestion.
- Tests для critical data paths.
- Не over-engineer MVP.

## 13. Tests

Обязательно тестировать критические случаи:
- one order → multiple executions;
- duplicate execId;
- repeated Filled order events;
- position event без реального position change;
- reconnect + reconciliation;
- missing execution recovery;
- known execution from REST не создаёт duplicate;
- candle gap/backfill;
- raw persistence при normalization error;
- Telegram event linking;
- voice persistence при STT failure;
- trader verification;
- удаление/замена связей: без отдельного подтверждения данные не меняются; отмена и устаревшее подтверждение безопасны; подтверждённое изменение сохраняет историю;
- dataset integrity/export.

## 14. Changes

При изменении data model, event semantics, reconciliation или storage:
- учитывать обратную совместимость;
- обновлять migration/schema;
- обновлять tests;
- обновлять README/PROJECT_INSTRUCTIONS при изменении архитектурного смысла;
- не менять silently смысл существующих fields.

## 15. Main rule

Если есть выбор между:
- красивой интерпретацией;
- сохранением исходной реальности;

выбирать сохранение исходной реальности.
