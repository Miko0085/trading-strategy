# Модель ордера

## Сущности, которые нельзя смешивать

```text
GridOrderConfig
    ↓
ExchangeOrder
    ↓
Execution / Fill
    ↓
StrategyLot / Filled Allocation
    ↓
TP / Partial Close / Full Close
```

## 1. GridOrderConfig — намерение трейдера

Хранит:
- номер уровня;
- Long / Short;
- процентный отступ;
- `configured_qty`;
- TP Steps;
- revision конфигурации.

Это описание того, **что система собирается сделать**, а не факт исполнения.

## 2. ExchangeOrder — реальная заявка на Bybit

Это конкретная биржевая заявка с собственным exchange order ID и состоянием.

Одна конфигурация может порождать одну или несколько биржевых заявок в течение её жизненного цикла, например после amend/cancel-replace.

## 3. Execution / Fill — факт сделки

Execution — фактическое исполнение на бирже.

Один ExchangeOrder может иметь несколько executions. Они не создают новые Grid Orders.

## 4. StrategyLot / Filled Allocation — фактически набранный объём стратегии

После **первого фактического fill** система уже должна отдельно учитывать исполненный объём конкретного Grid Order, потому что на него может быть выставлена разгрузка.

```text
configured_qty = 1.0

fill #1 = 0.3
→ filled_qty = 0.3
→ существует фактически набранный объём
→ можно рассчитать TP на 0.3

fill #2 = 0.2
→ filled_qty = 0.5
→ тот же логический StrategyLot / Filled Allocation обновляется
```

Архитектурно этот объект может иметь состояние `ACCUMULATING`, пока исходный Entry Order продолжает получать fills.

Это заменяет прежнюю модель, где Strategy Lot появлялся только после полного исполнения `configured_qty`.

## 5. Закрытия

TP или досрочное закрытие изменяют:
- `open_qty`;
- `closed_qty`;
- realized PnL конкретного объёма.

## История изменений

Любая правка через интерфейс должна сохранять:
- состояние до;
- состояние после;
- timestamp;
- источник изменения;
- Grid Revision;
- связь с ExchangeOrder / Execution / StrategyLot.

Цель — всегда уметь сопоставить **намерение → исполнение → результат**.
