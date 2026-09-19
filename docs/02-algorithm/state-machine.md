# Автоматы состояний и оркестратор

**Статус: АРХИТЕКТУРНАЯ МОДЕЛЬ / ЧАСТЬ СОСТОЯНИЙ ЕЩЁ УТОЧНЯЕТСЯ**

State Machines не принимают торговые решения. Они контролируют допустимые переходы уже существующих сущностей.

## 1. GridOrderState

Концептуально:

```text
CONFIGURED
→ ACTIVE
→ PARTIALLY_FILLED
→ FILLED
```

Также возможны:
- CANCELLED / DISABLED;
- REJECTED на уровне связанного ExchangeOrder.

## 2. StrategyLotState

После первого фактического fill появляется отдельно отслеживаемый исполненный объём.

```text
ACCUMULATING
→ ACTIVE
→ PARTIALLY_CLOSED
→ CLOSED
```

`ACCUMULATING` означает: Entry Grid Order ещё может получать дополнительные fills, но уже существует фактический объём, которым нужно управлять.

Точный переход `ACCUMULATING → ACTIVE` ещё требует технического определения.

## 3. TPStepState

```text
PENDING
→ ARMED
→ PLACED
→ PARTIALLY_FILLED?
→ FILLED
```

Дополнительно:
- MODIFIED;
- CANCELLED;
- REPLACED.

## 4. Grid Lifecycle Orchestrator

Оркестратор координирует сущности:

```text
Grid
├── GridRevision
├── GridOrderConfig
├── ExchangeOrder
├── StrategyLot
└── TPStep
```

Он:
- связывает executions с правильным Grid Order;
- обновляет filled_qty и average entry;
- инициирует синхронизацию TP;
- применяет утверждённую Grid Revision;
- гарантирует допустимые переходы состояния.

Он **не**:
- выбирает sizing;
- решает, когда реструктурировать Grid;
- рассчитывает новый капитал;
- принимает risk decisions.

Active Order Window — отдельная execution policy, а не state machine: [active-order-window.md](active-order-window.md).
