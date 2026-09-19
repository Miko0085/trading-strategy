# Будущий Risk Manager

**Статус: БУДУЩЕЕ / НЕЗАВИСИМЫЙ SAFETY И DECISION GATE**

Risk Manager — отдельный слой между планированием действий и реальным исполнением.

Он не является частью Restructuring Algorithm и не является частью Execution Engine.

## Контракт

```text
Strategy / Restructuring Planner
        ↓
Proposed Plan
        ↓
Risk Manager
        ↓
ALLOW / MODIFY / DENY
        ↓
Approved Execution Plan
        ↓
Execution Engine
```

## Что он потенциально будет проверять

- equity;
- available balance;
- available margin;
- margin reserve;
- Long exposure;
- Short exposure;
- gross exposure;
- allocation limits;
- concentration;
- liquidation distance;
- capital budget;
- ограничения по конкретной монете;
- минимальный необходимый запас капитала.

## Типы результата

### ALLOW
План может быть исполнен без изменений.

### MODIFY
План допустим только после ограничения параметров, например уменьшения qty или сохранения большего margin reserve.

Точные правила MODIFY пока не определены.

### DENY
Действие не передаётся в Execution Engine.

## Emergency actions

Только после отдельной формализации:
- block new entries;
- reduce exposure;
- early unload;
- emergency close.

## Risk Manager не прогнозирует рынок

Он отвечает не на вопрос «куда пойдёт цена», а на вопрос:

> Допустимо ли предложенное действие при текущем состоянии капитала и позиции?

Новости, sentiment, technical indicators и AI price prediction не используются.