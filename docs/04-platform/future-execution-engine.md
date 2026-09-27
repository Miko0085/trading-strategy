# Execution Engine — механизм безопасного исполнения

**Статус: FUTURE WRITE-CAPABLE COMPONENT / НЕ РЕАЛИЗОВАН**

Execution Engine не принимает стратегических решений. Он исполняет только уже утверждённый план.

## Вход

```text
ApprovedExecutionPlan
- PLACE / AMEND / CANCEL / TP / CLOSE actions
- symbol
- side / positionIdx
- price
- qty
- source Grid Revision
- instrument metadata snapshot
- idempotency key
```

## Обязанности

- повторно валидировать command перед отправкой;
- использовать актуальные Bybit instrument limits;
- обеспечивать idempotency;
- защищаться от duplicate command;
- отправлять write request;
- отслеживать REST acknowledgement и private WS factual state;
- связывать ExchangeOrder с GridOrderConfig;
- дедуплицировать executions;
- выполнять reconciliation;
- синхронизировать TP;
- сохранять command audit;
- восстанавливаться после restart/reconnect.

## Hard Technical Gate

Перед каждым PLACE/AMEND:

```text
instrument status valid
qty >= minOrderQty
qty aligned to qtyStep
notional >= minNotionalValue
price aligned to tickSize
position mode valid
metadata fresh enough for policy
```

Если command/plan невалиден:

```text
DO NOT SEND TO BYBIT
→ FAILED_PRE_EXECUTION_VALIDATION
→ MANUAL_REVIEW
```

Если план атомарный и один обязательный order invalid, Execution Engine не должен исполнять остальные команды как partial apply.

## Что Execution Engine не имеет права делать автоматически

- увеличивать qty до биржевого минимума;
- использовать Reserve без нового plan;
- переносить капитал между Long/Short;
- менять `K` / `M_i` / leverage / allocation;
- удалять невалидный Grid Order и продолжать;
- выбирать новый sizing;
- решать, куда реинвестировать прибыль;
- прогнозировать рынок.

## Active Order Window

Execution Engine механически поддерживает `active_order_count` текущей Grid Revision.

Queued GridOrderConfig не создаёт ExchangeOrder, пока не наступило разрешённое событие активации.

## Partial fills

После первого fill:
- создаётся/обновляется StrategyLot;
- обновляется factual `filled_qty`;
- пересчитывается factual average fill;
- TP1..TP4 работают только с factual open qty.

Уже исполненный объём нельзя отменить или уменьшить restructuring command.

## REST / WS semantics

REST acknowledgement не равен окончательному состоянию.

Execution Engine обязан корректно обрабатывать:
- REST timeout при фактически созданном order;
- WS event раньше REST response;
- duplicate WS/REST execution;
- out-of-order events;
- cancel/fill race;
- amend/partial-fill race;
- reconnect;
- restart.

Factual executions являются ground truth.

## Reconciliation

После reconnect/restart и при неопределённом command result:

```text
Platform Intent
vs
Actual Bybit Orders / Executions / Positions
```

Неопределённый результат не считается автоматически success или failure.

## External intervention

Если trader вручную меняет state на Bybit:

```text
DIFF
→ notify
→ block hidden strategic recalculation
→ Adopt or Restore after confirmation
```

Factual fills остаются immutable.

## Safety requirements

Обязательны:
- отдельный write-enabled API key;
- testnet/demo/paper-first;
- idempotency;
- orderLinkId/platform command correlation;
- command audit;
- reconciliation;
- restart recovery;
- kill switch;
- stale-state detection;
- hard instrument validation;
- no write path inside Recorder.
