# Bybit Strategy Recorder

Read-only Recorder для записи ручной торговли на Bybit V5. Он фиксирует состояние рынка и счёта, сохраняет сырые события, нормализует данные в SQLite и формирует аналитический набор данных.

**Recorder навсегда остаётся read-only и не размещает, не изменяет и не отменяет ордера.**

Отдельный **Execution Engine** может разрабатываться параллельно как самостоятельный компонент для механического исполнения заранее заданных трейдером параметров. Он не является частью Recorder.

Тестовый браузерный конструктор этой механики находится в [`execution_ui/`](execution_ui/README.md). Это автономный статический прототип без Bybit API и без возможности торговать: он рассчитывает Long/Short-сетку, активное окно, ограничения ордеров, partial fill и TP от фактически исполненного объёма.

Каноническая документация стратегии и платформы находится в **[`docs/`](docs/README.md)** и публикуется через GitBook.

Основной язык документации — **русский**. Технические названия полей, API и сущностей кода могут оставаться на английском, но пользовательские объяснения должны быть понятны русскоязычному трейдеру.

## Установка

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,telegram]'
cp .env.example .env
python scripts/init_db.py
pytest -q
```

Fill `.env` only with a dedicated Bybit V5 read-only key and optional Telegram/STT credentials. Secrets are never read from YAML or included in exports. `config/symbols.yaml` defines the permanent market watchlist and supported intervals, not a filter for account events; `symbols: []` is valid (relies entirely on `market.auto_discovery`). Edit `config/recorder.yaml` for storage and feature flags; `market.save_open_kline_updates_raw: false` skips RAW capture of unconfirmed (in-progress) kline WS pushes to reduce disk usage — closed candles (`save_closed_klines`) and all normalized data are unaffected either way, since unconfirmed candles are never used downstream.

## Автоматический сбор новых монет

Заранее добавлять торговую монету в YAML не требуется. Все символы из выбранных Private WS subscriptions проходят нормализацию. REST-сверка получает историю без фильтра по watchlist и обнаруживает открытые ордера/позиции в настроенной категории. Для `linear` текущие ордера/позиции запрашиваются по `reconciliation.settle_coins` (по умолчанию USDT и USDC).

При `market.auto_discovery: true` обнаруженные инструменты сохраняются в `tracked_instruments`. Для каждой новой монеты в настроенной категории запускается отдельное Public WS-подключение с теми же интервалами и настройками рынка, что у постоянного списка. Уже работающие подписки не прерываются. Обнаруженные монеты восстанавливаются после перезапуска; существующие нормализованные записи также используются для заполнения реестра. Для старых строк без категории применяется текущая категория конфигурации.

Ограничения:

- Автоматический рынок и REST работают в категории из `symbols.yaml` (например, `linear`), не одновременно во всех категориях. Private-события других категорий сохраняются, а отсутствие соответствующего рыночного покрытия отмечается gap.
- До первого ticker новой монеты snapshot может быть пустым. `market_before_discovery` отмечает отсутствие точных прежних котировок; backfill свечей не восстанавливает исторические bid/ask или точный snapshot события.
- Backfill запускается после подтверждения новой подписки и её reconnect, если он включён. При расширении области сверки используется настроенное стартовое окно истории, а не вся история аккаунта.
- `auto_discovery: false` выключает дополнительные рыночные подключения, но не сохранение account events.

Для автоматически обнаруженных монет (не из постоянного `symbols.yaml`) Public WS-подключение и сбор ticker/kline останавливаются, когда позиция по монете подтверждённо нулевая (наблюдался хотя бы один снимок позиции с size=0) и нет активных ордеров. Запись в `tracked_instruments` при этом не удаляется — сохраняется история и `stopped_at`; любое новое account-событие по этой монете (ордер, исполнение, позиция) автоматически снимает остановку и восстанавливает рыночное подключение при следующем цикле discovery. Пока нет ни одного наблюдения позиции, монета не считается «плоской» и не останавливается. Постоянный watchlist (`symbols.yaml`) эта логика не затрагивает — его подключение не останавливается независимо от состояния позиции.

`/status` показывает число активных автоматических рыночных подключений. Manifest содержит постоянный список (`configured_symbols`), полный реестр обнаруженных инструментов (включая остановленные, с `stopped_at`) и объединённый список активно отслеживаемых символов. Чтобы включить изменения в уже запущенном recorder, нужен штатный перезапуск; не запускайте второй процесс поверх первого.

## Создание read-only API key для sub-account

Recorder должен использовать API key именно того Bybit sub-account, на котором выполняется ручная торговля.

1. Войдите в Bybit под нужным sub-account.
2. Откройте `Account & Security` → `API Management`.
3. Нажмите `Create New Key` и выберите системный API key.
4. Установите режим `Read-Only`.
5. Включите только чтение данных:
   - `Derivatives/Contract`: чтение `Order` и `Position`;
   - `Wallet/Account` — только если это требуется интерфейсом для чтения баланса.
6. Не включайте `Spot Trade`, `Withdraw`, `Account Transfer`, `SubMember Transfer` и любые write/trading permissions.
7. Добавьте IP whitelist, если внешний IP recorder стабилен.
8. Сохраните `API Key` и `API Secret` сразу после создания. Secret повторно получить нельзя.

Заполните локальный `.env`:

```env
BYBIT_API_KEY=...
BYBIT_API_SECRET=...
BYBIT_TESTNET=false
```

Из master account sub-account API key также можно создать через управление sub-account, но для recorder предпочтителен отдельный read-only key самого торгового sub-account.

Bybit проверяется через `GET /v5/user/query-api`; recorder продолжает работу только при `readOnly=1`. Bybit может показывать `ContractTrade: ["Order", "Position"]` у read-only key — это права чтения состояния и истории, а не возможность отправлять ордера.

Официальная документация: [Create Sub UID API Key](https://bybit-exchange.github.io/docs/v5/user/create-subuid-apikey), [Get API Key Information](https://bybit-exchange.github.io/docs/v5/user/apikey-info).

## Состояние разработки: 0.2.0

Исправлены критические пути сохранения данных и восстановления. Подробности и ограничения: [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md).

- Один SQLite writer; событие, timeline, snapshot и аналитические проекции записываются одной транзакцией.
- RAW сохраняется первым, с capture ID, временем получения и индексом байтов. Ошибка нормализации не удаляет исходное сообщение.
- Public/Private WS проверяют подтверждения подписки; reconnect запускает восстановление.
- REST: только GET allowlist, точная подпись отправляемой строки, проверка retCode, пагинация и ограниченные повторы.
- Wallet, позиции Long/Short, PnL и funding сохраняются без подстановки выдуманных нулей. Денежные значения — decimal strings.
- Telegram: реальные event IDs, проверка владельца заметки, исправление текста и связей, история правок.
- Аудио сохраняется до STT; автоматические повторы и очередь доставки готовых расшифровок переживают перезапуск.
- Экспорт содержит SQLite snapshot, Parquet, RAW, аудио, конфигурацию без ENV, manifest и SHA-256.

## Запуск и обновление

Запускайте команды из корня проекта. Поддерживаемый локальный runtime — macOS/Linux, Python 3.12+.

```bash
python scripts/init_db.py
recorder
```

Перед обновлением остановите старый процесс recorder. Новая версия блокирует одновременную запись нескольких процессов в одну БД. Перед миграцией автоматически создаётся SQLite backup в `data/db/backups/`; старые строки не удаляются. Не удаляйте файл блокировки работающего процесса.

Без ключа запускается публичный сбор рынка — это **не офлайн-режим**. С ключом private-доступ разрешается только после проверки `readOnly=1`. Telegram и STT включаются согласно YAML и ENV. `BYBIT_TESTNET`, если задан, должен совпадать с `environment` в YAML.

Старые записи не становятся полными от одной миграции: новая схема не выдумывает недостающие снимки и связи.

## Проверка и экспорт без сетевых запросов

```bash
python -m pytest -q -W error
python -m ruff check src scripts tests
python scripts/inspect.py --symbol SUIUSDT --last 2h
python scripts/verify_dataset.py --strict
python scripts/export_dataset.py --experiment-id first-run
python scripts/verify_dataset.py --bundle data/exports/first-run --strict
```

Inspect и export не мигрируют рабочую БД. Экспорт создаёт новую папку; существующий эксперимент не перезаписывается. Manifest публикуется атомарно последним. Папка без manifest — незавершённый экспорт.

Verifier различает PASS / WARNING / FAIL. При FAIL код возврата 1; `--strict` также делает WARNING ошибкой. PASS означает прохождение реализованных проверок, а не доказательство полноты всей биржевой истории.

## Восстановление и обслуживание

Следующие команды используют сеть и записывают результаты в БД. Сначала остановите recorder:

```bash
python scripts/reconcile.py --reason manual
python scripts/backfill_market.py --symbol SUIUSDT --interval 1 --hours 2
python scripts/retry_transcription.py --voice-id ID --reset-attempts
```

Public backfill не требует API key. Reconciliation требует read-only ключа. Retry STT отправляет сохранённое аудио провайдеру и может расходовать API-баланс; текст не выводится в консоль. Исправленный трейдером текст не перезаписывается транскрипцией.

Офлайн replay биржевых RAW — только в новую отдельную БД:

```bash
python scripts/replay_raw.py --raw data/raw --output-db data/recovered.sqlite
```

Replay не заменяет backup: он не восстанавливает Telegram-диалоги, системные сессии и аудио. Старые REST klines без параметров запроса восстановить однозначно нельзя; такие записи учитываются как ошибки.

## Telegram и расшифровка

`TELEGRAM_ALLOWED_USER_ID` — ID пользователей через запятую. `TELEGRAM_ALLOWED_CHAT_ID` — ID разрешённых чатов. Если заданы оба списка, пользователь должен принадлежать первому, а чат — второму. Если задан только chat ID, доступ получают участники этого чата; для группы с несколькими людьми рекомендуется дополнительно ограничить пользователей.

Для STT: `TRANSCRIPTION_PROVIDER=openai` и `TRANSCRIPTION_API_KEY`. Используется `gpt-4o-mini-transcribe`; аудио передаётся внешнему провайдеру. Без настроенного провайдера аудио остаётся pending, попытки не расходуются. После исчерпания автоматических попыток доступен явный maintenance retry.

Telegram может присылать OGG с расширением `.oga`. Для OpenAI проверяется сигнатура `OggS`, и только имя загружаемого файла меняется на `.ogg`; оригинал не переименовывается и не перекодируется. Поддерживаемые форматы указаны в [OpenAI API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create).

Ошибки STT сохраняют безопасные HTTP status/code/retryable, но не тело ответа и не ключи. Постоянные отказы (например, HTTP 400/401 или insufficient_quota) не повторяются автоматически; после устранения причины используйте maintenance retry. Временные сетевые ошибки, 429 rate limit и 5xx обрабатываются ограниченными повторами.

`/status` показывает WS-сессии, последнее событие, сверку, свечи, gaps и ожидающие аудио. `/recent` показывает последние 10 событий (ORDER/EXECUTION/POSITION) и позволяет выбрать несколько для одного пояснения; кнопки «Показать раньше ↓» / «Показать позже ↑» листают историю порциями по 10 в обе стороны, выбор сохраняется между страницами. `/recent ГГГГ-ММ-ДД` показывает события конкретной даты. Навигация и переключение событий обновляют одно и то же сообщение (`editMessageText`), а не создают новое при каждом нажатии. Подтверждение заметки не означает подтверждение торгового правила.

Bybit-событие `execution` с `execType=Funding` сохраняется в dataset, но не представляется как торговый fill. В Telegram оно подписывается как начисление funding («не сделка») и по умолчанию не отправляется. Отдельное уведомление можно включить через `telegram.notifications.funding: true`; флаг `executions` на funding не распространяется.

Пояснение с событиями подтверждается кнопкой «Подтвердить текст и события». Без связей доступно только явное «Подтвердить как общее пояснение»; это не подтверждение торгового действия. В `context_json.confirmation_scope` сохраняется `event` или `general`. Старые подтверждения без этого поля сохраняются как исторические, их смысл автоматически не переопределяется.

При исправлении связей ссылки и `event_contexts` обновляются одной транзакцией; прежний контекст сохраняется в `link_context_history`. `at_note_time` остаётся исходным снимком на момент пояснения. Изменение текста/связей сбрасывает подтверждение, требует новой проверки и делает прежнюю кнопку неактуальной. Отсутствующий before/after сохраняется как NULL, а не заменяется текущим состоянием.

## Семантика данных и ограничения

`current_states` — последнее наблюдаемое состояние, не независимая гарантия актуальности биржи. `observations` содержит версии, before/after-контекст и provenance. `account_balances`, `coin_balances`, `position_balances`, `pnl_records` — аналитические проекции этих наблюдений. Версии одного closed-PnL результата нельзя безусловно суммировать.

`totalAvailableBalance` сохраняется как сообщённая доступная маржа; для режимов, где Bybit не возвращает поле, остаётся NULL. Funding хранит отдельные официальные funding/cashFlow/fee, без самодельного объединения знаков. Изменения mark price/uPnL без изменения позиции не объявляются действием трейдера.

Market snapshot использует последнюю полученную котировку и хранит её возраст; это не синхронный снимок биржи в момент исполнения. При sampled ticker сохраняется исходный выбранный delta и дополнительный объединённый контекст для replay; пропущенные обновления RAW не заявляются сохранёнными.

REST способен восстановить исполнения и доступные состояния, но не все промежуточные изменения сетки, кошелька и позиции во время disconnect. Поэтому startup/reconnect могут завершаться WARNING даже при успешных запросах. Возможная перестройка сетки — описательная группировка, а не доказанное намерение трейдера.

Официальные схемы: [V5 authentication](https://bybit-exchange.github.io/docs/v5/guide), [WS connect](https://bybit-exchange.github.io/docs/v5/ws/connect), [wallet](https://bybit-exchange.github.io/docs/v5/account/wallet-balance), [positions](https://bybit-exchange.github.io/docs/v5/position), [closed PnL](https://bybit-exchange.github.io/docs/v5/position/close-pnl), [transaction log](https://bybit-exchange.github.io/docs/v5/account/transaction-log).

Экспорты содержат приватную историю аккаунта, тексты и голос трейдера: храните их как конфиденциальные данные, даже если API secrets исключены.
