# Recorder — роль

**Статус: OBSERVED FACT** — описывает уже реализованный компонент (`src/recorder/`). Recorder не переписывается и не дублируется этой документацией.

## Что делает Recorder

Recorder фиксирует:

- Bybit market/account events (WebSocket public + private, REST reconciliation);
- orders, executions, positions, wallet;
- trader actions (через Telegram);
- trader notes (текст и голос);
- config changes;
- timeline — агрегированную человекочитаемую последовательность событий.

## Чего Recorder не делает

Он **не является торговым ботом**: в коде нет `place_order`, `amend_order`, `cancel_order`, `close_position`, `set_leverage`, `set_tp_sl`. Private-коллектор работает только с read-only Bybit API key; ключ с trading-правами не допускается к запуску.

## Разделение источников истины

```
Machine truth   = Bybit (ордера, исполнения, позиции, wallet — факт)
Trader reasoning = объяснение трейдера (текст/голос через Telegram)
```

Эти два слоя **никогда не смешиваются** в хранилище: у события есть его объективные данные, и отдельно — привязанные (и явно подтверждённые трейдером) пояснения.

## Основная исследовательская цепочка

```
STATE BEFORE
  → MARKET / ACCOUNT CONTEXT
  → TRADER ACTION
  → ORDER EVENTS
  → EXECUTIONS
  → STATE AFTER
  → TRADER EXPLANATION
  → RESULT
```

Именно эта цепочка используется при заполнении [05-research/trader-observations.md](../05-research/trader-observations.md) — каждая запись там должна быть проверяема по этой структуре и по ID событий в БД Recorder'а.

## Где искать техническую документацию Recorder'а

Технические детали (установка, конфигурация, WS/REST-механика, схема БД, экспорт, Telegram-команды) находятся в корневом [`README.md`](../../README.md), [`PROJECT_INSTRUCTIONS.md`](../../PROJECT_INSTRUCTIONS.md) и [`DEVELOPMENT_RULES.md`](../../DEVELOPMENT_RULES.md) — эта папка их не дублирует, а ссылается на них.
