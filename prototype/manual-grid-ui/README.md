# Manual Grid UI MVP

Изолированный MVP для ручной настройки Long Grid и Short Grid. Это отдельный будущий Execution Engine-контур: он не импортируется Recorder'ом, не использует Recorder SQLite и не содержит Bybit write endpoints.

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

Открыть `http://localhost:5173`. Если Bybit credentials не заданы, интерфейс API показывает безопасные demo account values; реальные private данные появляются только после read-only проверки ключа.

## ENV

- `DATABASE_URL` — PostgreSQL нового модуля;
- `BYBIT_API_KEY`, `BYBIT_API_SECRET` — отдельный read-only ключ, не ключ Recorder;
- `BYBIT_TESTNET` — `true`/`false`;
- `MANUAL_GRID_ALLOWED_ORIGINS` — origin frontend.

Backend при наличии ключа вызывает только `GET /v5/user/query-api` перед private integration и отказывается запускаться, если `readOnly != 1`. В коде отсутствуют place/amend/cancel/close/write методы.

## Migration

```bash
psql "$DATABASE_URL" -f migrations/001_initial.sql
```

## Tests

```bash
cd prototype/manual-grid-ui
pip install -r backend/requirements.txt
PYTHONPATH=backend pytest -q tests
cd frontend && npm test -- --run
```

Проверяются Decimal-расчёты цены, weighted average, TP/P&L, allocation guard, полная сетка против лимита и read-only boundary. Production order placement, automatic restructuring, automatic sizing, AI decisions и Risk Manager намеренно не входят в MVP.
