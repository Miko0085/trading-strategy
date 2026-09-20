# Manual Grid UI MVP — инструкции для реализации

## Цель

Создать изолированный веб-интерфейс для ручной настройки Long Grid и Short Grid с базовыми расчётами, чтением текущего состояния Bybit через существующий read-only API key и сохранением истории изменений.

Этот модуль **не должен изменять существующий Recorder, его БД, runtime или папку docs/**.

## Безопасное размещение в репозитории

Создавать новый изолированный модуль только здесь:

```text
prototype/manual-grid-ui/
├── frontend/
├── backend/
├── migrations/
├── tests/
├── .env.example
├── docker-compose.yml
├── README.md
└── IMPLEMENTATION_PROMPT.md
```

Запрещено для MVP:
- менять `src/recorder/`;
- импортировать trading/write-логику в Recorder;
- менять существующую Recorder SQLite;
- менять файлы в `docs/`;
- менять существующие raw/normalized Recorder data;
- использовать write-enabled Bybit API key;
- place/amend/cancel реальные ордера;
- добавлять автоматическую реструктуризацию;
- добавлять автономные trading decisions.

## Рекомендуемый стек

### Frontend
- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui или эквивалентные простые компоненты

### Backend
- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy 2.x или SQLModel
- Alembic

### Database
- PostgreSQL

### Почему такой стек

Frontend остаётся TypeScript, потому что браузерный UI, формы, realtime state и типизированные API-контракты удобнее реализовывать в React/TypeScript.

Backend здесь лучше сделать Python/FastAPI, а не Node/Fastify, потому что текущий repository и Recorder уже Python 3.12+. Это снижает количество runtime-стеков внутри одного проекта и упрощает передачу проекта разработчику.

## Общая архитектура MVP

```text
Browser UI
    ↓
Manual Grid API
    ↓
Calculation Service
Capital Allocation Guard
Revision / Audit Service
    ↓
PostgreSQL

Параллельно:

Manual Grid API
    ↓
Bybit Read-Only Adapter
    ↓
Bybit V5 REST / Private WS
```

Новый модуль не должен зависеть от Recorder runtime.

## Bybit

Использовать текущий read-only API key только через ENV нового backend.

Пример:

```env
BYBIT_API_KEY=
BYBIT_API_SECRET=
BYBIT_TESTNET=false
DATABASE_URL=postgresql+psycopg://...
```

Никогда не коммитить secrets.

При старте backend проверить через официальный Bybit V5 API, что ключ read-only. Если ключ имеет write/trading permissions, backend MVP должен отказать в запуске private-account integration.

Использовать только официальную Bybit V5 документацию. Не придумывать endpoints или fields.

Для MVP нужны read-only данные:
- баланс аккаунта;
- equity;
- available balance / available margin;
- initial margin;
- maintenance margin;
- открытые позиции;
- активные ордера;
- Mark Price выбранного инструмента;
- instrument limits.

Для realtime:
- Private Wallet WS;
- Private Position WS;
- при необходимости Private Order/Execution WS только для чтения;
- REST reconciliation через безопасный интервал.

Wallet WS не считать единственным источником доступной маржи. Нужна периодическая REST-сверка.

## Язык интерфейса

Весь пользовательский интерфейс — русский.

Не показывать пользователю backend-поля:
- configured_qty;
- filled_qty;
- entry_offset_pct;
- minOrderQty;
- minNotionalValue;
- GridRevision;
- TPStepState.

Показывать:
- Объём ордера;
- Исполнено;
- Осталось;
- Отступ от текущей цены;
- Отступ от предыдущего ордера;
- Цена входа;
- Средняя цена;
- Take Profit;
- Закрыть объём;
- Активен;
- В очереди;
- Частично исполнен;
- Исполнен;
- Доступная маржа;
- Лимит;
- Остаток лимита.

## Один экран

Не использовать вкладки Long / Short.

Desktop layout:

```text
┌──────────────────────────────────────────────────────────────────┐
│ Bybit Account / Symbol / Capital Allocation / History / Save    │
├──────────────────────┬──────────────────────┬────────────────────┤
│ LONG GRID            │ ОБЩИЙ РАСЧЁТ        │ SHORT GRID         │
│                      │                      │                    │
│ Order #1             │ Текущая цена        │ Order #1           │
│ Order #2             │ Long avg            │ Order #2           │
│ Order #3             │ Short avg           │ Order #3           │
│ ...                  │ Exposure / P&L       │ ...                │
│                      │ Capital indicators   │                    │
└──────────────────────┴──────────────────────┴────────────────────┘
```

На небольшом экране колонки могут складываться вертикально, но не превращаться в отдельные функциональные вкладки.

## Верхняя панель аккаунта

Показывать:
- выбранный инструмент;
- текущую Mark Price;
- баланс кошелька;
- equity;
- доступную маржу;
- initial margin;
- maintenance margin;
- время последнего обновления Bybit;
- статус соединения.

## Распределение доступной маржи

Allocation считается **от актуальной доступной маржи аккаунта Bybit**, а не от вручную введённого стартового баланса.

Пользователь задаёт проценты, например:
- Long — 40%;
- Short — 20%;
- Резерв — 40%.

Сумма должна быть 100%.

На каждом обновлении available margin пересчитать денежные лимиты:

```text
long_limit = available_margin × long_pct
short_limit = available_margin × short_pct
reserve = available_margin × reserve_pct
```

Это базовое конфигурируемое правило MVP.

## Capital Allocation Guard

Не позволять сохранить/активировать конфигурацию, если плановая маржа полной логической сетки превышает выделенный лимит соответствующей стороны.

Проверять всю сетку, а не только активное окно.

Для каждой стороны показывать:
- Разрешено;
- Уже занято существующей позицией;
- Требуется активными ордерами;
- Требуется очередью;
- Всего запланировано;
- Осталось;
- % использования лимита.

Если лимит превышен:
- красный индикатор;
- точная сумма превышения;
- блокировка активации/подготовки Execution Plan.

Не блокировать обычное редактирование Draft.

## Визуальный индикатор allocation

Сделать полукруглый gauge в стиле Fear & Greed meter, но смысл — использование выделенного лимита.

Пример:

```text
LONG
          72%
     ╭──────────╮
 LOW │    ▲     │ LIMIT
     ╰──────────╯

Использовано: $2,880
Лимит:        $4,000
Осталось:     $1,120
```

Не называть его «страх/жадность».

Названия:
- «Использование лимита Long»
- «Использование лимита Short»
- «Резерв маржи»

Цветовые warning thresholds пока считать UI-конфигурацией, а не стратегическим правилом. Hard stop только при >100%.

## Long Grid и Short Grid

Обе стороны видны одновременно.

Каждая сторона имеет:
- количество логических уровней;
- количество одновременно активных Entry Orders;
- фактическую среднюю цену открытой позиции;
- плановую среднюю цену при исполнении всей настроенной сетки;
- фактический открытый объём;
- плановый общий объём;
- фактическую маржу;
- плановую маржу;
- остаток allocation.

Long и Short конфигурируются независимо.

## Карточка Grid Order

Пользователь видит:

- № ордера;
- статус;
- отступ;
- расчётную цену входа;
- объём в монетах;
- стоимость позиции;
- плановую маржу;
- фактическую среднюю цену этого ордера, если есть fills;
- исполненный объём;
- открытый объём;
- реализованный P&L этого Strategy Lot, если данные доступны;
- Take Profit steps;
- заметку.

### Отступ

Не использовать слово Offset.

Order #1:
- Long: «Отступ от текущей цены, %»
- Short: «Отступ от текущей цены, %»

Order #2+:
- «Отступ от предыдущего ордера, %»

Цена рассчитывается автоматически.

## Средняя цена

Обязательно показывать три уровня:

1. Средняя цена конкретного Grid Order / Strategy Lot по фактическим fills.
2. Общая фактическая средняя цена Long стороны.
3. Общая фактическая средняя цена Short стороны.

Дополнительно рассчитывать:
- плановую среднюю Long при полном исполнении настроенной сетки;
- плановую среднюю Short при полном исполнении настроенной сетки;
- накопительную среднюю после каждого следующего уровня.

Все средние — quantity-weighted.

Не смешивать фактическую среднюю Bybit side position с attribution по отдельному Grid Order.

## Take Profit

Для каждого Grid Order разрешить несколько TP.

Пользователь задаёт:
- процент движения от фактической/плановой цены входа;
- процент закрываемого объёма.

UI рассчитывает:
- цену TP;
- количество монет;
- gross P&L;
- комиссии, если fee rate доступен/настроен;
- плановый net P&L;
- остаток объёма после TP.

Если ордер ещё не исполнен — показатели помечать «План».

Если есть fills — расчёты строить от фактической средней цены этого Grid Order.

## Общая панель расчёта

В центральной колонке показывать:

### Текущая позиция
- Mark Price;
- Long avg;
- Short avg;
- Long qty;
- Short qty;
- Net exposure;
- Gross exposure.

### Плановая сетка
- Long planned qty;
- Short planned qty;
- Long planned margin;
- Short planned margin;
- плановая средняя Long;
- плановая средняя Short.

### Take Profit
- плановый gross P&L Long;
- плановый gross P&L Short;
- плановый gross P&L общий;
- оценка комиссий;
- плановый net P&L.

Плановый P&L — это не прогноз рынка. Это арифметический результат при условии исполнения конкретно настроенных Entry и TP.

## Price Ladder

В центральной части добавить компактную визуальную лестницу:

```text
SHORT #5
SHORT #4
SHORT #3
SHORT #2
SHORT #1
──────── Mark Price ────────
LONG #1
LONG #2
LONG #3
LONG #4
LONG #5
```

Показывать рассчитанные цены.

## Active Order Window

Это уже рабочая логика MVP.

Пример:
- 20 Long levels;
- active order count = 5.

Состояние:
- #1–#5 Active/Prepared;
- #6–#20 Queued.

Когда Exchange Adapter позже получит факт исполнения одного активного Entry Order, Grid Engine должен активировать следующий queued level, чтобы поддерживать заданное active count.

В текущем MVP реальных write-команд Bybit нет. Логику Active Window реализовать в домене и тестах, но до подключения write-enabled Execution Adapter она не отправляет реальные ордера.

## Никакого ручного переключения execution status

Пользователь не должен вручную устанавливать:
- Filled;
- Partially Filled;
- Cancelled.

Эти статусы являются exchange/runtime state.

Пока write execution не подключён, UI показывает конфигурационные состояния:
- Черновик;
- Подготовлен;
- В очереди.

После будущего подключения Bybit Execution Engine statuses поступят из Exchange Adapter.

## История

Каждое изменение пользователя сохранять в audit log:
- дата;
- время;
- entity;
- действие;
- before;
- after.

В UI кнопка «История изменений» открывает modal/drawer со списком по времени.

Фильтры:
- Все;
- Long;
- Short;
- Ордеры;
- Take Profit;
- Настройки капитала;
- Настройки сетки.

## Grid Revision

Кнопка «Сохранить версию».

Revision — immutable snapshot текущей конфигурации.

Хранить:
- Long Grid;
- Short Grid;
- allocations;
- active order counts;
- все Order configs;
- все TP configs;
- reference market snapshot;
- timestamp;
- optional comment.

Нельзя изменять уже сохранённую revision.

## База данных

Использовать PostgreSQL для нового UI-модуля.

Не использовать Recorder SQLite как operational DB нового интерфейса.

Причина:
- UI audit;
- revisions;
- realtime account state;
- будущие execution commands;
- конкурентные процессы;
- дальнейшее подключение Bybit Execution Engine.

Recorder SQLite остаётся отдельным источником machine truth Recorder.

## Минимальные таблицы нового модуля

- ui_accounts
- grids
- grid_revisions
- grid_order_configs
- tp_step_configs
- allocation_configs
- account_snapshots
- audit_events

Заложить, но не активировать real execution:
- execution_plans
- execution_commands

## Calculation Service

Все финансовые расчёты должны быть отдельными pure functions/service и покрыты unit tests.

Минимум:
- Entry price chain;
- position notional;
- estimated initial margin;
- weighted average price;
- cumulative weighted average;
- TP price;
- TP qty;
- gross P&L;
- fee estimate;
- net P&L;
- Long/Short allocation limits;
- remaining allocation;
- full-grid planned margin;
- active-window planned margin.

Использовать Decimal, не binary float, для денежных/ценовых расчётов.

## Не реализовывать сейчас

- automatic restructuring;
- compound capital recalculation rules;
- automatic volume recovery;
- AI decisions;
- automatic spacing;
- automatic sizing;
- production trading writes;
- write-enabled API key;
- autonomous Risk Manager;
- news/signals/indicators.

## Тесты

Обязательно:
- Long Order #1 от Mark Price;
- Short Order #1 от Mark Price;
- subsequent order price chain;
- weighted average per order;
- weighted average whole Long/Short side;
- cumulative average;
- allocation = percentage of live available balance;
- available balance update recalculates limits;
- full Grid over allocation => blocked;
- active window under limit but full Grid over limit => blocked;
- reserve cannot be consumed by Long/Short planning;
- TP qty/P&L calculations;
- revision immutability;
- audit event on each config change;
- read-only API key validation;
- backend contains no Bybit write endpoint.

## Definition of Done

MVP готов, когда трейдер может:
1. Открыть один русский экран.
2. Увидеть живые read-only данные своего Bybit account.
3. Задать % Long / Short / Reserve.
4. Увидеть денежные allocation limits от текущей available margin.
5. Построить Long и Short Grid вручную.
6. Настроить каждый ордер независимо.
7. Настроить несколько TP для каждого ордера.
8. Сразу видеть Entry price, margin, averages и плановый P&L.
9. Видеть фактическую среднюю каждого исполненного объёма, Long и Short после появления exchange data.
10. Не иметь возможности активировать сетку, превышающую allocation.
11. Настроить Active Order Window.
12. Сохранить immutable Grid Revision.
13. Открыть полную историю своих изменений.
14. Не иметь ни одного production Bybit write-action в этом MVP.
