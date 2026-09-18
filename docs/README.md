# Strategy Capture — документация

Эта папка (`docs/`) — **каноническая база знаний по стратегии и платформе** проекта Bybit Strategy Recorder / Strategy Capture. Она предназначена для:

- трейдера;
- разработчика;
- AI/Codex-агента;
- будущего исследователя стратегии.

Основной язык — русский. Технические сущности (`Strategy Lot`, `Grid Order`, `original_qty`, `remaining_qty`, `PnL` и т.п.) оставлены на английском, так как это имена полей/концепций в коде и данных.

## Что здесь НЕ находится

- Код Recorder'а (`src/recorder/`) — это отдельный технический слой, описанный здесь только на уровне роли и архитектуры (см. [04-platform/recorder-role.md](04-platform/recorder-role.md)), но не переписывается и не дублируется.
- Сырые торговые данные, кошельки, voice-файлы, API-ключи — эта папка описывает **знание о стратегии**, а не raw dataset аккаунта.

## Структура

| Раздел | Содержание |
|---|---|
| [00-overview/](00-overview/project-overview.md) | Что за проект, цели, принципы, глоссарий |
| [01-strategy/](01-strategy/strategy-overview.md) | Механика стратегии: Long/Short, grid, ордера, partial TP |
| [02-algorithm/](02-algorithm/current-algorithm.md) | Текущий подтверждённый алгоритм/жизненный цикл |
| [03-risk/](03-risk/risk-register.md) | Реестр рисков, будущий Risk Manager |
| [04-platform/](04-platform/platform-overview.md) | Платформа, роль Recorder, интеграция с Bybit, модель данных |
| [05-research/](05-research/trader-observations.md) | Наблюдения, candidate/confirmed rules, открытые вопросы, противоречия |
| [06-development/](06-development/roadmap.md) | Roadmap, changelog, журнал решений |

## Текущая фаза проекта

**BASE STRATEGY MECHANICS** — формализуем механику (Long/Short, grid orders, Strategy Lots, partial TP), ничего не автоматизируя. Подробнее: [06-development/roadmap.md](06-development/roadmap.md).

## Главный принцип

Стратегия — детерминированная математическая система на основе цены и состояния аккаунта. Внешние сигналы (индикаторы, новости, sentiment, AI-прогнозы) не используются. Подробнее: [00-overview/principles.md](00-overview/principles.md).

## Как читать статусы знания

Каждое утверждение в этой документации помечено статусом:

| Статус | Значение |
|---|---|
| `OBSERVED FACT` | Факт из Bybit/Recorder (timeline, ордера, исполнения) |
| `TRADER EXPLANATION` | Объяснение трейдера, ещё не формальное правило |
| `CANDIDATE` | Возможное правило, требует подтверждения/повторения |
| `CONFIRMED` | Правило явно подтверждено трейдером |
| `EXPERIMENTAL` | Механика обсуждается/тестируется |
| `FUTURE` | Будущая функция, сейчас не реализуется |
| `OPEN QUESTION` | Нужен ответ трейдера |
| `REJECTED` | Рассматривалось и отвергнуто |
| `CONTRADICTION` | Две несовместимые версии, требуют разрешения |

Никогда не повышать `CANDIDATE`/`OBSERVED FACT` до `CONFIRMED` без явного подтверждения трейдера — см. [06-development/decisions.md](06-development/decisions.md).

## Публикация

GitHub — source of truth. GitBook подключён через Git Sync и рендерит содержимое этой папки как есть (см. `.gitbook.yaml` в корне репозитория). Ручной копии документации внутри GitBook не создаётся.
