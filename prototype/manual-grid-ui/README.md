# Manual Grid UI MVP

Изолированный MVP для ручной настройки лонг- и шорт-сетки. Это отдельный будущий execution-контур: он не импортируется Recorder'ом, не использует Recorder SQLite и не содержит Bybit write endpoints.

## Состав

- `frontend/` — React + TypeScript + Vite, один русский экран с обеими сторонами сетки.
- `backend/` — Python 3.12+ + FastAPI, read-only Bybit adapter и API ревизий.
- `migrations/` — PostgreSQL schema для аккаунтов, grids, revisions, TP, allocation, snapshots и audit.
- `tests/` — backend calculation/read-only tests.

## Запуск

```bash
cd prototype/manual-grid-ui
cp .env.example .env
docker compose up -d postgres
psql "$DATABASE_URL" -f migrations/001_initial.sql

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload --port 8000
```

В отдельном терминале:

```bash
cd prototype/manual-grid-ui/frontend
npm install
npm run dev
```

Открыть `http://localhost:5173`. Если read-only ключ не найден или backend недоступен, интерфейс показывает `нет данных` и блокирует расчёт/сохранение; фиктивные балансы и цены не используются.

## ENV

- `DATABASE_URL` — PostgreSQL нового модуля, только process env или `prototype/manual-grid-ui/.env`;
- `BYBIT_API_KEY`, `BYBIT_API_SECRET` — read-only ключ; process env → UI `.env` → root `.env`;
- `BYBIT_TESTNET` — `true`/`false`, с тем же приоритетом только для Bybit;
- `MANUAL_GRID_ALLOWED_ORIGINS` — origin frontend, только process env или UI `.env`;
- `MANUAL_GRID_ALLOW_FIXTURE_DATA` — только локальный тестовый режим, по умолчанию `false`;
- `MANUAL_GRID_STALE_AFTER_SECONDS` — технический порог устаревания account state, по умолчанию `30`.

Root `.env` не переносится и не импортируется как конфигурация Recorder: из него читаются только три ключа Bybit, когда они не заданы process env или UI `.env`. `DATABASE_URL` и UI-настройки из root `.env` игнорируются.

Backend получает factual `mark_price`, `totalAvailableBalance` и instrument filters сам через read-only Bybit. Значения из браузера являются только intent/preview и не участвуют в production authoritative calculation. Capital Guard использует `full_grid_planned_margin / allocation_limit × 100`; текущая позиция показывается отдельным factual context и не вычитается второй раз из available margin.

Округление к tick size сейчас является техническим preview/calculation policy. Перед любым будущим write execution правила округления должны быть отдельно подтверждены.

Backend при наличии ключа вызывает только `GET /v5/user/query-api` перед private integration и отказывается запускаться, если `readOnly != 1`. В коде отсутствуют place/amend/cancel/close/write методы.

Диагностика подключения без секретов:

```bash
curl http://localhost:8000/api/health
curl 'http://localhost:8000/api/diagnostics/bybit?symbol=BTCUSDT'
curl http://localhost:8000/api/state/BTCUSDT
```

При ошибке read-only проверки backend продолжает запускаться с `private_state_ready=false`; public market endpoints остаются доступными. `/api/diagnostics/bybit` показывает только наличие credentials, источник bundle, окружение и статусы query-api/wallet/positions/open-orders.

## Migration

```bash
psql "$DATABASE_URL" -f migrations/001_initial.sql
psql "$DATABASE_URL" -f migrations/002_hardening.sql
```

## Tests

```bash
cd prototype/manual-grid-ui
pip install -r backend/requirements.txt
PYTHONPATH=backend pytest -q tests
cd frontend && npm test -- --run
```

Текущий MVP использует REST polling/reconciliation; архитектура `AccountStateService` оставляет место для будущих Wallet/Position/Order WebSocket и REST reconciliation. Проверяются Decimal-расчёты цены, weighted average, TP/P&L, allocation guard, полная сетка против лимита, normalized account state, stale state, read-only boundary, ENV isolation и API-контракт. Production order placement, automatic restructuring, automatic sizing, AI decisions и Risk Manager намеренно не входят в MVP.
## Open questions

- В Hedge Mode нужно отдельно подтвердить семантику отсутствующей zero-side position для gross/net exposure. До подтверждения нормализация сохраняет отсутствующую сторону как `null` и не подставляет искусственный нулевой размер.
- Audit фиксируется при сохранении immutable revision, а не на каждое изменение draft-поля.
