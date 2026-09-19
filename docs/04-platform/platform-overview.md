# Архитектура платформы

**Статус: RECORDER РЕАЛИЗОВАН / EXECUTION CORE ПРОЕКТИРУЕТСЯ / DECISION И RISK LAYERS ФОРМАЛИЗУЮТСЯ**

## Основной поток

```text
Trader Configuration / Confirmed Strategy Rules
                    ↓
             Decision Layer
        ┌───────────┴───────────┐
        ↓                       ↓
Base Grid Planner      Restructuring Planner
                                ↓
                         RestructuringPlan
                                ↓
                           Risk Manager
                      ALLOW / MODIFY / DENY
                                ↓
                     Approved Execution Plan
                                ↓
                         Execution Engine
                                ↓
                              Bybit
```

Параллельно и независимо:

```text
Bybit
 ↓
Recorder
 ↓
Research / Reconciliation / Dataset
```

## 1. Strategy / Configuration Layer

Содержит подтверждённые правила и параметры, заданные трейдером. Прямого write-path к Bybit у него нет.

## 2. Decision Layer

### Base Grid Planner
Строит механический план текущей Grid Revision: уровни, qty, active order window и TP configuration.

### Restructuring Planner
Формирует новый RestructuringPlan. Он не отправляет ордера напрямую.

## 3. Risk Manager

Независимый safety/decision gate. Возвращает ALLOW / MODIFY / DENY.

## 4. Execution Engine

Execution Engine должен быть максимально детерминированным.

Он:
- получает уже утверждённый план;
- валидирует биржевые ограничения;
- создаёт/amend/cancel ExchangeOrders;
- синхронизирует TP;
- поддерживает idempotency;
- ведёт command audit;
- делает reconciliation ожидаемого и фактического состояния.

Он не должен:
- придумывать sizing;
- решать, когда реструктурировать Grid;
- менять capital allocation;
- принимать risk decisions.

## 5. Recorder

Recorder навсегда остаётся read-only и фиксирует фактическую реальность Bybit независимо от decision layer.

## 6. Ручное вмешательство через Bybit

```text
Expected Platform State
≠
Actual Bybit State
↓
Notify Trader
↓
Require Confirmation
↓
Adopt external state
OR
Restore platform state where technically safe
```

Уже произошедшие executions не компенсируются автоматически.

## Жёсткие границы

```text
Decision Layer = что хотим сделать
Risk Manager   = можно ли это делать
Execution      = как безопасно исполнить
Recorder       = что реально произошло
```

Эти ответственности нельзя объединять в один модуль.