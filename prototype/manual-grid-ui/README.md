# Manual Grid UI MVP

Изолированный MVP для ручной настройки Long/Short Grid с read-only Bybit factual state, automatic future sizing и manual volume restructuring.

Основной пользовательский режим — **Manual Grid**. Veles-like Generated Grid остаётся дополнительным/legacy constructor и не определяет текущий основной workflow.

Модуль не импортируется Recorder'ом, не использует Recorder SQLite и не содержит production Bybit write endpoints.

## Состав

- `frontend/` — React + TypeScript + Vite;
- `backend/` — Python 3.12+ + FastAPI;
- `migrations/` — PostgreSQL schema для revisions/audit/shadow state;
- `tests/` — calculation/read-only/shadow tests.

## Текущий целевой workflow

```text
Symbol
→ Factual Bybit State
→ Long / Short / Reserve Allocation
→ Manual Grid Geometry
→ Price or Percentage per level
→ Per-Order Martingale
→ Automatic Future Qty
→ Active Order Window
→ Manual RECALCULATE_ORDER / RECALCULATE_GRID
```

Factual fills являются immutable. Пересчитывается только future/pending quantity.

## Запуск

```bash
cd prototype/manual-grid-ui
cp .env.example .env
docker compose up -d postgres
psql "$DATABASE_URL" -f migrations/001_initial.sql
psql "$DATABASE_URL" -f migrations/002_hardening.sql
psql "$DATABASE_URL" -f migrations/003_shadow_simulation.sql

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Frontend:

```bash
cd prototype/manual-grid-ui/frontend
npm install
npm run dev
```

Открыть `http://localhost:5173`.

## ENV

- `DATABASE_URL` — PostgreSQL нового модуля;
- `BYBIT_API_KEY`, `BYBIT_API_SECRET` — read-only key;
- `BYBIT_TESTNET` — `true`/`false`;
- `MANUAL_GRID_ALLOWED_ORIGINS` — comma-separated frontend origins;
- `MANUAL_GRID_ALLOW_FIXTURE_DATA` — только локальный тестовый режим;
- `MANUAL_GRID_STALE_AFTER_SECONDS` — порог устаревания factual state.

Секреты не коммитить. `VITE_*` frontend variables нельзя использовать для Bybit/API/DB secrets.

## Factual Bybit State

Backend получает factual data сам:
- Mark Price;
- wallet/equity/available margin;
- positions;
- open orders;
- instrument limits;
- position mode.

Значения из браузера являются intent и не должны заменять authoritative factual state.

Backend проверяет read-only key через Bybit и не должен выполнять private write actions.

Диагностика:

```bash
curl http://localhost:8000/api/health
curl 'http://localhost:8000/api/diagnostics/bybit?symbol=BTCUSDT'
curl http://localhost:8000/api/state/BTCUSDT
```

## Manual Grid Geometry

Для каждого уровня планируется поддержка:
- абсолютной Entry Price;
- либо процентного spacing.

#1 относительно reference Mark Price, #2+ может задаваться относительно предыдущего уровня.

Grid Geometry и Grid Sizing независимы.

## Per-Order Martingale

В основном Manual Grid каждый следующий уровень имеет собственный multiplier:

```text
w1 = 1
w2 = w1 × M2
w3 = w2 × M3
...
```

Глобальный `M^i` остаётся только частью optional Generated Grid.

## Automatic Future Sizing

Целевой calculation pipeline:

```text
Effective Side Budget
- Factual Used Capital
- Locked Future Capital
= Available Future Budget

Available Future Budget
→ cumulative per-order weights
→ normalized level budgets
→ leverage
→ entry price
→ coin qty
→ ROUND_DOWN by qtyStep
→ Bybit min validations
```

Ключевые поля:

```text
configured_qty
filled_qty
remaining_entry_qty
open_qty
closed_qty
```

Invariant:

```text
configured_qty >= filled_qty
configured_qty = filled_qty + remaining_entry_qty
```

## Manual Volume Restructuring

Два подтверждённых scope:

### RECALCULATE_ORDER

Пересчитывает future qty только выбранного Grid Order. Остальные уровни не должны автоматически изменяться.

### RECALCULATE_GRID

Получает fresh factual state и перераспределяет весь eligible future budget стороны между pending levels по текущей cumulative Martingale chain.

Добавленный новый уровень может быть рассчитан отдельно либо включён в полный перерасчёт сетки.

## Active Order Window

Полная логическая Grid может быть больше количества одновременно активных Entry orders на Bybit.

Трейдер задаёт `active_order_count` независимо для Long и Short. Остальные levels остаются queued внутри платформы.

## Generated Grid

Текущий Generated Grid не удаляется.

Подтверждённые формулы:
- normalized power distribution для geometry;
- legacy/global geometric martingale `w_i = M^(i-1)`.

Это secondary constructor, а не основной Manual Grid workflow.

## Shadow API

Текущие endpoints `POST /api/shadow/generate` и `POST /api/shadow/restructure` создают только virtual proposals и не вызывают write API.

Существующий код shadow sizing ещё должен быть приведён к новой Manual Grid per-order Martingale модели; документация описывает целевую подтверждённую механику, а не утверждает, что весь код уже реализован.

## Tests

```bash
cd prototype/manual-grid-ui
PYTHONPATH=backend pytest -q tests
cd frontend
npm test -- --run
npm run build
```

После изменения sizing/restructuring обязательны новые tests на:
- PRICE/PERCENT geometry;
- cumulative per-order Martingale;
- factual capital subtraction;
- `RECALCULATE_ORDER`;
- `RECALCULATE_GRID`;
- immutable filled_qty;
- adding new levels;
- Active Order Window;
- Bybit instrument limits.

## Локальные черновики

Workspace хранится в browser `localStorage` и содержит только пользовательский intent. Factual Bybit state, secrets, API credentials и authoritative calculations туда не записываются.

Persistence привязан к browser origin. Для постоянной web-ссылки используется стабильный Pages/custom domain, а backend может быть доступен через отдельный постоянный HTTPS endpoint/tunnel.

## Не входит в текущий автоматический MVP

- automatic restructuring triggers;
- automatic recovery;
- automatic reinvest triggers;
- autonomous rebase/trailing decisions;
- AI trading decisions;
- external news/signals/indicators;
- production write execution без отдельного решения;
- autonomous Risk Manager.
