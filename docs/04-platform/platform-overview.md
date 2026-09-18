# Platform Overview

**Статус: OBSERVED FACT (Recorder) / FUTURE (остальное)**

Платформа концептуально состоит из слоёв:

```
┌─────────────────────────────────────────┐
│  Strategy / Platform documentation       │  ← docs/ (эта папка)
│  (эта папка: правила, алгоритм, roadmap) │
├─────────────────────────────────────────┤
│  Future Execution Engine   (FUTURE)      │  ← ещё не существует
│  Future Risk Manager       (FUTURE)      │
├─────────────────────────────────────────┤
│  Bybit Strategy Recorder   (EXISTS)      │  ← src/recorder/, реализовано
│  read-only, без торговых вызовов         │
├─────────────────────────────────────────┤
│  Bybit V5 (Exchange)                     │
└─────────────────────────────────────────┘
```

## Что уже существует

Только **Recorder** (`src/recorder/`) — read-only система записи рыночных и аккаунт-событий. Она не размещает, не изменяет и не отменяет ордера. Роль подробно — [recorder-role.md](recorder-role.md), интеграция с Bybit — [bybit-integration.md](bybit-integration.md), модель данных — [data-model.md](data-model.md).

## Что не существует (FUTURE)

Execution Engine и Risk Manager — будущие компоненты, которые появятся только после формализации стратегии (Phase 2+, см. [06-development/roadmap.md](../06-development/roadmap.md)). Черновое описание — [future-execution-engine.md](future-execution-engine.md) и [03-risk/future-risk-manager.md](../03-risk/future-risk-manager.md).

## Границы ответственности

- **Recorder** отвечает за то, «что произошло» (machine truth) и «что сказал трейдер» (trader reasoning), не смешивая их.
- **docs/** отвечает за накопленное знание о стратегии, извлечённое из данных Recorder'а плюс объяснений трейдера.
- **Future Execution Engine / Risk Manager** — единственные компоненты, которые в будущем смогут отправлять реальные торговые вызовы, и то только после отдельного явного решения (см. правило в [06-development/decisions.md](../06-development/decisions.md)).
