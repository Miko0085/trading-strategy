# Обзор проекта

**Статус: ПОДТВЕРЖДЁННАЯ АРХИТЕКТУРА / ЧАСТИЧНО ОТКРЫТАЯ CAPITAL ROUTING LOGIC**

## Главная цель

Платформа автоматизирует детерминированную Long/Short Grid-стратегию в Hedge Mode, сохраняя приоритет безопасности капитала, маржи и позиции.

## 1. Recorder — что реально произошло

Permanently read-only контур:
- orders;
- executions;
- positions;
- wallet;
- market/account state;
- trader notes;
- timeline.

Recorder никогда не торгует.

## 2. Strategy / Configuration

Хранит:
- Manual Grid Geometry;
- Long/Short allocation;
- leverage;
- sizing mode;
- `K` / `M_i`;
- Active Order Window;
- TP1..TP4;
- Grid Revision.

## 3. Sizing / Planning

Рассчитывает future intent:

```text
Future Margin Budget
→ Future Notional Budget
→ POWER_CURVE или PER_ORDER_M
→ notional_i
→ qty_i
```

Sizing не меняет factual fills.

## 4. Restructuring Planner

Формирует новый future plan после manual command или confirmed profit-taking trigger.

Routing нового capital между Long/Short пока OPEN.

## 5. Technical Validation

Проверяет актуальные Bybit instrument limits и техническую исполнимость всего plan.

Любой mandatory invalid order → `MANUAL_REVIEW`, без partial apply.

## 6. Risk Manager

Отдельно оценивает capital/margin/exposure/liquidation risk и возвращает ALLOW/MODIFY/DENY.

## 7. Execution Engine

Детерминированно исполняет только approved plan через Bybit API, обеспечивает idempotency, reconciliation, audit и restart recovery.

## 8. Research

Формализует оставшиеся неизвестные правила:
- production `capital_base`;
- reinvestable capital;
- Long/Short routing;
- recovery/trailing;
- risk thresholds.

## Главная архитектурная формула

```text
CONFIGURATION = что настроил трейдер
SIZING        = сколько future capital получает каждый order
VALIDATION    = технически исполним ли plan
RISK          = безопасен ли plan
EXECUTION     = как отправить commands
RECORDER      = что реально произошло
```
