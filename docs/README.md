# Документация торговой стратегии

Эта папка (`docs/`) — **каноническая база знаний по стратегии и платформе**.

Документация предназначена для:
- трейдера;
- разработчика;
- AI/Codex/Claude-агента;
- будущего исследователя стратегии.

Основной язык — русский. Английские технические названия сохраняются для связи с кодом/API.

## Текущий канонический scope

Основной продуктовый workflow:

```text
Manual Long / Short Grid
→ independent Geometry
→ POWER_CURVE или PER_ORDER_M sizing
→ Margin → Notional → Qty
→ Bybit hard validation
→ Active Order Window
→ Factual Executions / StrategyLots
→ TP1..TP4
→ Profit-taking restructuring trigger
```

Ключевые ограничения:
- Recorder permanently read-only;
- factual fills immutable;
- Generated Grid — legacy/optional;
- другие Martingale modes вне `POWER_CURVE` и `PER_ORDER_M` сейчас не входят в MVP;
- любой mandatory order ниже Bybit limits блокирует весь новый plan и переводит его в `MANUAL_REVIEW`;
- capital routing между Long и Short пока остаётся исследовательским вопросом.

## Главные страницы

- [Обзор стратегии](01-strategy/strategy-overview.md)
- [Механика сетки](01-strategy/grid-mechanics.md)
- [Мартингейл и распределение объёма](01-strategy/martingale-sizing.md)
- [Алгоритм реструктуризации](02-algorithm/restructuring-algorithm.md)
- [Интеграция с Bybit](04-platform/bybit-integration.md)
- [Модель данных](04-platform/data-model.md)
- [Подтверждённые правила](05-research/confirmed-rules.md)
- [Открытые вопросы](05-research/open-questions.md)
- [Журнал решений](06-development/decisions.md)

## Что здесь не публикуется

- API secrets;
- private account/wallet dumps;
- реальные order/event IDs;
- voice files;
- private raw trading history.

## Статусы знаний

| Статус | Значение |
|---|---|
| **OBSERVED FACT** | факт из Bybit / Recorder |
| **TRADER EXPLANATION** | объяснение логики трейдером |
| **CANDIDATE** | гипотеза, требующая подтверждения |
| **CONFIRMED** | явно подтверждённое правило |
| **EXPERIMENTAL** | тестируемая механика |
| **FUTURE** | будущая функция |
| **OPEN QUESTION** | нерешённый вопрос |
| **REJECTED** | отвергнутая идея |
| **SUPERSEDED** | правило заменено новым подтверждением |
| **CONTRADICTION** | несовместимые версии требуют уточнения |

Нельзя повышать CANDIDATE до CONFIRMED без явного подтверждения.

GitHub является source of truth, GitBook публикует содержимое `docs/` через Git Sync.
