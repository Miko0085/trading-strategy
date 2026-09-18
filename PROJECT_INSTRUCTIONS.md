# BYBIT STRATEGY RECORDER — PROJECT INSTRUCTIONS

> Перед изменением логики стратегии/платформы сначала прочитайте `docs/README.md` и:
> `docs/00-overview/principles.md`, `docs/01-strategy/strategy-overview.md`, `docs/02-algorithm/current-algorithm.md`, `docs/05-research/confirmed-rules.md`, `docs/05-research/open-questions.md`, `docs/06-development/decisions.md`.

## 1. Основной контекст

Мы создаём систему для исследования, документирования и последующей формализации существующей ручной торговой стратегии криптовалютного трейдера на Bybit.

Трейдер уже торгует вручную. На текущем этапе наша задача — **не создать торгового бота**, а максимально точно записать рынок, состояние аккаунта, Long/Short позиции, ордера, фактические исполнения, PnL, действия трейдера, его объяснения и результат этих действий.

Стратегия пока не формализована полностью и во многом находится в голове трейдера. Поэтому используем подход:

> Сначала наблюдаем реальное поведение → документируем причины → находим повторяющиеся закономерности → подтверждаем их у трейдера → только затем превращаем в алгоритм.

Текущая система — **Strategy Recorder / black-box recorder**, а не Strategy Engine.

## 2. Главная модель данных

Для каждого существенного торгового решения должно быть возможно восстановить:

```text
STATE BEFORE
    ↓
MARKET CONTEXT
    ↓
ACCOUNT / POSITION / GRID STATE
    ↓
TRADER ACTION
    ↓
ORDER EVENTS
    ↓
ACTUAL EXECUTIONS
    ↓
STATE AFTER
    ↓
TRADER EXPLANATION
    ↓
FINANCIAL RESULT
```

Сокращённо:

```text
MARKET STATE
+ ACCOUNT STATE
+ TRADER ACTION
+ EXECUTION
+ TRADER EXPLANATION
+ RESULT
```

## 3. Текущая стадия

```text
OBSERVE
↓
RECORD
↓
SYNCHRONIZE
↓
DOCUMENT
↓
VERIFY
↓
EXPORT
```

Система пока **не должна принимать торговые решения и торговать**.

## 4. Критический запрет на trading

Strategy Recorder является READ-ONLY системой.

На текущем этапе запрещено реализовывать:
- создание, изменение и отмену ордеров;
- закрытие позиций;
- автоматический TP/SL;
- изменение leverage;
- автоматическое управление сеткой;
- автоматическое управление Long/Short;
- автоматическую ребалансировку;
- AI trading;
- signal generation.

Не создавать `place_order()`, `cancel_order()`, `amend_order()`, `close_position()` даже «на будущее».

Используется отдельный READ-ONLY Bybit API key. Если ключ имеет write/trading permissions, private collector не должен запускаться.

## 5. Что известно о стратегии

Известный исследовательский контекст:
- Hedge Mode;
- одновременно Long и Short;
- сетки лимитных ордеров;
- разные объёмы ордеров;
- увеличение объёма глубже по сетке;
- частичные фиксации;
- перестройка оставшихся ордеров;
- использование реализованного PnL и доступной маржи;
- изменение распределения капитала между Long и Short;
- управление средними ценами Long/Short;
- положительный floating/unrealized PnL одной стороны может учитываться при решениях по другой стороне.

Это **не означает**, что точные математические правила уже установлены.

Пока нельзя самостоятельно считать подтверждёнными:
- формулу расстояния между grid orders;
- martingale sizing;
- процент partial close;
- Take Profit;
- Long/Short allocation;
- restructuring formula;
- формулу использования unrealized PnL;
- price zones;
- combined break-even formula.

## 6. Не додумывать стратегию

Никогда не превращать наблюдение или пример в универсальное правило без подтверждения трейдера.

Различать:

### LEVEL 1 — Observed Fact
Объективно произошло: например, отменено 6 Long orders и создано 6 новых.

### LEVEL 2 — Trader Explanation
Трейдер объяснил, почему он это сделал.

### LEVEL 3 — Confirmed Strategy Rule
Правило формализовано и явно подтверждено трейдером.

Только Level 3 в будущем может использоваться как официальный алгоритм.

Если объяснения противоречат друг другу — не выбирать «более логичное». Зафиксировать противоречие и запросить уточнение.

## 7. Bybit и объяснения трейдера

Bybit — источник машинной истины о том, **что фактически произошло**.

Trader explanation — источник информации о том, **почему трейдер совершил действие**.

Эти слои нельзя смешивать.

## 8. Order ≠ Execution

`order` описывает жизненный цикл заявки: New, PartiallyFilled, Filled, Cancelled и т. п.

`execution` описывает фактическое исполнение.

Один order может иметь несколько executions. Поэтому нельзя создавать фактическую сделку только потому, что `orderStatus = Filled`.

Execution data является основным источником факта fill. Raw order events при этом также сохраняются полностью.

## 9. Три уровня хранения

### LEVEL 1 — JSONL
Append-only raw black box. Сохраняем максимально исходные сообщения Bybit.

### LEVEL 2 — SQLite + WAL
Нормализованная operational database: orders, executions, positions, wallet, market, timeline, notes, voice, reconciliation.

### LEVEL 3 — Parquet
Переносимый аналитический dataset для Python/Polars/Pandas/DuckDB/AI/reverse engineering.

Основной pipeline:

```text
SOURCE EVENT
↓
RAW SAVE
↓
NORMALIZATION
↓
SQLITE
```

Если normalizer падает, RAW event не должен быть потерян.

## 10. Bybit data

Минимальные Private V5 streams:
- order;
- execution;
- position;
- wallet.

Все сообщения выбранных private subscriptions сохраняются RAW.

Market context:
- минимум непрерывные 1-minute OHLCV candles;
- дополнительные candle intervals через YAML;
- realtime Last Price;
- Mark Price;
- Index Price;
- Best Bid / Best Ask.

При значимых account events создаётся market snapshot максимально близко к событию.

## 11. Конфигурация

Symbols и candle intervals нельзя hardcode.

Использовать `config/symbols.yaml`.

Список `symbols` — постоянный watchlist рынка, а не фильтр торговых событий аккаунта. События всех символов выбранных Private WS subscriptions должны сохраняться независимо от watchlist. Обнаруженные инструменты сохраняются в `tracked_instruments` и восстанавливаются при перезапуске. При включённом `market.auto_discovery` рынок новых монет подключается автоматически без разрыва существующих подписок.

Граница текущей реализации: автоматические Public WS и REST-сверка работают в одной настроенной категории; для текущих linear-ордеров/позиций используются `reconciliation.settle_coins` (USDT/USDC по умолчанию). Private-события других категорий не отбрасываются, но отсутствие рыночного покрытия отмечается явно. История до обнаружения монеты не считается полной: свечи можно запросить через backfill, точные прежние котировки нельзя выдумывать. Первый snapshot при отсутствии ticker остаётся пустым. Отключение автоподключения рынка не должно отключать запись торговых событий.

Пример:

```yaml
exchange: bybit
category: linear

symbols:
  - SUIUSDT

market:
  primary_kline_interval: "1"

  kline_intervals:
    - "1"
    - "15"
    - "60"
    - "120"
    - "240"
    - "720"

  ticker:
    enabled: true
    raw_recording: sampled
    sample_interval_seconds: 1

  public_trades:
    enabled: false

  orderbook:
    enabled: false
    depth: 1
```

Монеты, интервалы и market streams должны меняться без изменения Python-кода.

## 12. WebSocket reliability

Нельзя предполагать, что WebSocket непрерывен.

```text
WS DISCONNECT
↓
RECONNECT
↓
REST RECONCILIATION
↓
COMPARE WITH LOCAL DATA
↓
RECOVER MISSING EVENTS
↓
DEDUPLICATE
```

Reconciliation выполняется при startup, после reconnect и периодически.

Если полноту периода доказать невозможно — создать DATA GAP. Проблемы качества dataset нельзя скрывать.

## 13. Telegram

Telegram — интерфейс документирования стратегии, а не raw notification feed.

Весь Trader UX — **на русском языке**.

Допустимы привычные термины Long, Short, PnL, Limit, Take Profit, Stop Loss.

Raw collector сохраняет технические события отдельно, а Telegram показывает human-level events. Например 7 Cancel + 7 New Orders могут отображаться как одно событие «Перестроена Long-сетка».

Трейдер может выбрать событие и пояснить его текстом или голосом.

Один Trader Note может быть связан с несколькими underlying events.

Удалять существующие связи пояснения с событиями без явного подтверждения трейдера запрещено. Это касается и замены события: прежняя связь не удаляется автоматически. Сначала показать конкретное пояснение и удаляемые связи, затем запросить отдельное подтверждение удаления. Снятие отметки в интерфейсе и обычное сохранение выбора не заменяют это подтверждение. До подтверждения существующие данные остаются неизменными; после него прежние связи и контекст сохраняются в истории. Подробные требования — в `DEVELOPMENT_RULES.md`, раздел «Удаление связей пояснение → событие».

## 14. Голосовые пояснения

Pipeline:

```text
TELEGRAM VOICE
↓
SAVE ORIGINAL AUDIO
↓
SPEECH-TO-TEXT
↓
VERBATIM TRANSCRIPT
↓
EVENT LINKING
↓
TRADER VERIFICATION
```

Не смешивать:
1. Original Audio
2. Verbatim Transcript
3. AI Interpretation

Оригинальное аудио не удаляется автоматически.

После транскрипции трейдер получает связанные события и текст с кнопками:
- ✅ Всё верно
- 🔗 Исправить связь
- 📝 Исправить текст

После подтверждения `verified = true`.

## 15. Unified Timeline

Общая шкала объединяет:
- MARKET;
- ORDER;
- EXECUTION;
- POSITION;
- WALLET;
- TRADER_NOTE;
- VOICE_NOTE;
- RECONCILIATION;
- SYSTEM.

Когда возможно, отдельно хранить `exchange_timestamp` и `received_timestamp`.

Storage timezone: UTC.

## 16. Приоритеты reliability

Приоритеты:
1. Не потерять RAW data.
2. Не потерять execution.
3. Не задвоить execution.
4. Восстановиться после disconnect.
5. Сохранить объяснение трейдера.
6. Правильно связать его с контекстом.
7. UI и красивые отчёты — после этого.

Если Telegram падает — recorder продолжает работать.
Если STT падает — voice сохраняется.
Если normalizer падает — RAW остаётся.
Если export падает — JSONL + SQLite остаются.
Если reconciliation падает — фиксируется warning/data-gap risk.

## 17. Не собирать огромные потоки без причины

По умолчанию не требуется постоянно сохранять полный order book, L50/L200/L1000, каждую public trade и каждый 100ms ticker update в normalized DB.

Если позже будет подтверждено, что трейдер использует стакан/tape, соответствующие collectors можно включить.

## 18. Текущий stack

```text
Python 3.12+
asyncio

Bybit V5 REST
Bybit V5 WebSocket

JSONL
SQLite + WAL
Parquet

Telegram Bot API
Speech-to-Text provider
pytest
```

MVP рассчитан примерно на одного трейдера, один account/subaccount, несколько symbols и 1–2 недели наблюдений. Не добавлять Kafka/Redis/Kubernetes/microservices без объективной необходимости.

## 19. Будущие стадии

После накопления данных:

1. Reverse Engineering — поиск повторяющихся patterns.
2. Rule Confirmation — формулировка candidate rules и подтверждение трейдером.
3. Strategy Formalization — формальные strategy modules.
4. Shadow Mode — алгоритм рассчитывает действия, но не торгует.
5. Simulation/Testnet.
6. Automated Execution — только отдельным решением после предыдущих этапов.

## 20. Definition of Success

Текущий этап успешен, если после 1–2 недель ручной торговли можно точно восстановить:
- что происходило на рынке;
- состояние аккаунта;
- Long/Short позиции;
- активные ордера;
- действия трейдера;
- фактические исполнения;
- изменения позиций/PnL;
- объяснение причины действия;
- финансовый результат;
- наличие/отсутствие data gaps.

## 21. Главный принцип

> Сначала зафиксировать реальность.
>
> Потом понять логику.
>
> Потом подтвердить правила.
>
> И только потом автоматизировать торговлю.

Никогда не менять этот порядок ради ускорения разработки.
