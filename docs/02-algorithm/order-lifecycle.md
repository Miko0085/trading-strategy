# Жизненные циклы ордеров

**Статус: БАЗОВАЯ ДОМЕННАЯ МОДЕЛЬ**

Нужно различать жизненный цикл **GridOrderConfig** и жизненный цикл **ExchangeOrder**.

## GridOrderConfig — логический уровень стратегии

Пример состояний:

```text
CONFIGURED
→ ACTIVE
→ PARTIALLY_FILLED
→ FILLED

или

CONFIGURED / ACTIVE
→ DISABLED / REMOVED
```

Точные enum-названия могут измениться при реализации.

GridOrderConfig хранит намерение стратегии и не равен биржевой заявке.

## ExchangeOrder — реальная заявка Bybit

Типовой жизненный цикл:

```text
New
→ PartiallyFilled
→ Filled

New / PartiallyFilled
→ Cancelled

New
→ Rejected
```

Один GridOrderConfig может иметь несколько ExchangeOrder во времени, например при cancel-replace.

Один ExchangeOrder может иметь несколько Execution / Fill.

## Главное правило

```text
GridOrderConfig ≠ ExchangeOrder ≠ Execution
```

- GridOrderConfig — что хотели сделать;
- ExchangeOrder — что отправили на биржу;
- Execution — что реально исполнилось.

После первого Execution появляется фактически набранный объём стратегии, даже если Entry ExchangeOrder ещё не Filled полностью.

Отменить можно оставшуюся неисполненную часть ExchangeOrder. Уже случившиеся executions не отменяются.
