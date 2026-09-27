# Интеграция с Bybit

**Статус: RECORDER READ-ONLY РЕАЛИЗОВАН / WRITE EXECUTION ПРОЕКТИРУЕТСЯ**

## Каналы данных

- Public WebSocket — market data;
- Private WebSocket — orders, executions, positions, wallet;
- REST — reconciliation, history, account state, instrument metadata;
- Recorder использует только read-only methods;
- будущий Execution Engine использует отдельный write-enabled key.

## Execution является ground truth

1. `Execution / Fill` — факт сделки.
2. REST create/amend/cancel acknowledgement не считается окончательным factual state.
3. Один ExchangeOrder может иметь несколько executions.
4. Duplicate WS/REST events должны дедуплицироваться по factual identifiers.
5. После reconnect/restart выполняется REST reconciliation.

## Instrument Metadata

Актуальные ограничения инструмента должны загружаться из Bybit V5 Instruments Info:

```text
GET /v5/market/instruments-info
```

Для linear/perpetual минимум нужны:
- `minOrderQty`;
- `qtyStep`;
- `minNotionalValue`;
- `maxOrderQty` / applicable max;
- `tickSize`;
- status инструмента.

Эти данные нельзя хардкодить глобально.

## Instrument Metadata Cache

Платформа должна хранить локальный snapshot/cache, например:

```text
InstrumentSpec
- category
- symbol
- status
- min_order_qty
- qty_step
- min_notional_value
- max_order_qty
- tick_size
- fetched_at
- raw_payload_hash / source reference
```

Decimal/string representation предпочтительнее binary float.

Metadata обновляется:
- при старте backend;
- периодически;
- перед будущим PLACE/AMEND, если cache stale;
- при validation/restructuring snapshot для воспроизводимости.

## Hard Pre-Execution Validation

Перед запуском стратегии, после sizing/restructuring и перед каждым фактическим PLACE/AMEND:

```text
instrument status valid
qty >= minOrderQty
qty aligned to qtyStep
notional >= minNotionalValue
price aligned to tickSize
```

Если любой обязательный order общего плана невалиден:

```text
PLAN_INVALID
→ MANUAL_REVIEW
→ NO PARTIAL APPLY
```

Execution Engine не должен автоматически увеличивать qty, использовать Reserve, пропускать level или менять sizing parameters.

## Hedge Mode

Position mode должен определяться factual Bybit state.

Для Hedge Mode логически различаются Long и Short sides. Если mode неизвестен, simultaneous two-side execution должен fail closed до reconciliation/manual review.

## REST / WS race handling

Обязательные сценарии:
- REST timeout, но order фактически создан;
- WS event пришёл раньше REST response;
- cancel одновременно с fill;
- amend одновременно с partial fill;
- duplicate execution;
- out-of-order events;
- reconnect;
- restart recovery.

Для create operations нужна idempotency strategy (`orderLinkId` или эквивалентная platform command id).

## Grid Preview

Chart визуализирует текущую Manual Grid:
- Mark Price;
- Long/Short Entry levels;
- factual/planned qty;
- sizing weights;
- Active/Queued state.

Generated Grid preview не должен быть обязательным источником данных для основного UI.

## Источник истины по API

Используется актуальная официальная документация Bybit V5. API field semantics, instrument limits и account/margin fields нельзя восстанавливать предположениями.
