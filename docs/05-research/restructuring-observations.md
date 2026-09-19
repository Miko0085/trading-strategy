# Наблюдения по реструктуризации

**Статус: RESEARCH / STRATEGY CAPTURE**

Этот документ описывает не сам алгоритм, а то, какие данные нужно собирать, чтобы восстановить реальную логику реструктуризации трейдера.

## Основная исследовательская единица

```text
STATE BEFORE
↓
TRADER INTENT
↓
TRADER ACTION
↓
GRID REVISION
↓
ACTUAL BYBIT EXECUTION
↓
STATE AFTER
↓
RESULT
```

## Состояние до решения

- Mark Price;
- Long size;
- Short size;
- average entry;
- Strategy Lots;
- realized PnL;
- unrealized PnL;
- balance;
- equity;
- available margin;
- текущий allocation;
- margin reserve;
- активные Entry Orders;
- активные TP Orders;
- текущая Grid Revision.

## Намерение трейдера

- почему он решил менять сетку;
- какой результат ожидал;
- хотел ли восстановить разгруженный объём;
- хотел ли улучшить average entry;
- хотел ли перераспределить capital;
- хотел ли начать новый Grid cycle.

## Действие трейдера

- какие orders оставил;
- какие отменил;
- какие изменил;
- какие добавил;
- какие qty изменил;
- какие TP изменил;
- был ли rebase;
- изменился ли allocation.

## После действия

Recorder должен позволять восстановить:
- какие ExchangeOrders реально были выставлены;
- какие Executions произошли;
- сколько объёма было набрано;
- сколько было разгружено;
- realized PnL;
- изменение average entry;
- изменение available margin;
- изменение equity;
- дальнейшее действие трейдера.

## RestructuringEvent

```text
RestructuringEvent
- timestamp
- symbol
- side
- state_before
- trader_reason
- trader_action
- grid_revision_before
- grid_revision_after
- orders_kept
- orders_cancelled
- orders_amended
- orders_added
- qty_reallocated
- realized_pnl_context
- unrealized_pnl_context
- available_margin_before
- available_margin_after
- result
```

## Главная цель

Сопоставить:

```text
что трейдер собирался сделать
vs
что он реально сделал
vs
что фактически произошло на Bybit
vs
какой получился результат
```

И только после повторяющихся подтверждённых случаев превращать наблюдения в формальное правило Restructuring Algorithm.