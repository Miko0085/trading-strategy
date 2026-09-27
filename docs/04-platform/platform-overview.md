# Архитектура платформы

**Статус: RECORDER РЕАЛИЗОВАН / SIZING И EXECUTION CORE ПРОЕКТИРУЮТСЯ**

## Основной поток

```text
Trader Configuration / Confirmed Rules
                    ↓
             Planning Layer
        ┌───────────┴───────────┐
        ↓                       ↓
Base Grid Planner      Restructuring Planner
        ↓                       ↓
      Sizing Engine (POWER_CURVE / PER_ORDER_M)
                    ↓
           Technical Validation
       Bybit limits / position mode
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

Параллельно:

```text
Bybit
 ↓
Recorder
 ↓
Research / Reconciliation / Dataset
```

## Strategy / Configuration

Хранит Manual Geometry, allocation, leverage, sizing mode, coefficients, Active Window, TP1..TP4 и revisions.

## Sizing Engine

Распределяет только future budget.

Поддерживаются два MVP mode:
- `POWER_CURVE`;
- `PER_ORDER_M`.

Он не меняет factual fills и не решает Long↔Short routing.

## Technical Validation

До Risk Manager/Execution plan должен пройти актуальные exchange constraints:
- instrument status;
- `minOrderQty`;
- `qtyStep`;
- `minNotionalValue`;
- `tickSize`;
- position mode.

Любой обязательный invalid order:

```text
MANUAL_REVIEW
NO PARTIAL APPLY
```

## Risk Manager

Оценивает capital/margin/exposure/liquidation risk. Не исправляет биржевые минимумы и не прогнозирует рынок.

## Execution Engine

Механически исполняет ApprovedExecutionPlan, обеспечивает idempotency, REST/WS reconciliation, restart recovery и audit.

Он не придумывает sizing/routing.

## Recorder

Permanently read-only. Фиксирует machine truth независимо от platform intent.

## Profit-taking trigger

Profitable TP/close создаёт новый factual state refresh и restructuring proposal. Automatic routing/apply policy пока OPEN.

## External intervention

```text
Expected Platform State
≠
Actual Bybit State
↓
Notify
↓
Adopt / Restore after confirmation
```

Уже случившиеся executions immutable.

## Жёсткие границы

```text
Planning  = что хотим сделать
Sizing    = сколько future capital получает каждый order
Validation= технически исполним ли plan
Risk      = безопасен ли plan
Execution = как отправить и подтвердить commands
Recorder  = что реально произошло
```
