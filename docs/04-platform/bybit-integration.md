# Bybit Integration

**Статус: OBSERVED FACT** — уже реализовано в `src/recorder/bybit/`.

## Каналы

- **Public WebSocket** — kline, tickers (реалтайм рыночные данные).
- **Private WebSocket** — order, execution, position, wallet (реалтайм аккаунт-события).
- **REST** — только GET allowlist, используется для reconciliation, recovery, history и backfill. Никаких write-эндпоинтов.

## Ключевые инварианты

1. **Execution = факт исполнения.** Не путать со статусом ордера `Filled` — см. [02-algorithm/order-lifecycle.md](../02-algorithm/order-lifecycle.md).
2. **Raw payload сохраняется первым**, до нормализации (JSONL, append-only, до SQLite). Ошибка нормализации не удаляет исходное сообщение.
3. **Дедупликация — на уровне нормализованного слоя**, не на RAW. RAW никогда не удаляется из-за дедупликации.
4. **Один order может иметь несколько executions.**
5. **Read-only key проверяется явно** (`GET /v5/user/query-api`, `readOnly=1`) перед стартом private-коллектора.
6. **Reconnect** восстанавливает подписки и запускает сверку (reconciliation) — учитывает partial executions и duplicate/repeated события.

## Официальные источники (не устаревшие)

Актуальная официальная документация Bybit V5 — единственный источник истины по полям/эндпоинтам; примеры V2/V3 не используются. Ссылки — в корневом [`README.md`](../../README.md).
