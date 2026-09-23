# Обзор стратегии

**Статус: ПОДТВЕРЖДЁННАЯ БАЗОВАЯ МЕХАНИКА + ОТКРЫТЫЕ АВТОМАТИЧЕСКИЕ РЕШЕНИЯ**

## Текущий основной workflow

На текущем этапе стратегия строится вокруг ручной настройки геометрии сетки и автоматического расчёта будущего объёма.

```text
Trader Configuration
→ Manual Grid Geometry
→ Capital Allocation
→ Per-Order Martingale Chain
→ Automatic Future Qty
→ Active Order Window
→ Execution
→ Factual Fills / StrategyLots
→ Manual Volume Restructuring
```

Generated Grid остаётся дополнительным конструктором и не является основным режимом MVP.

## Что уже подтверждено

- стратегия поддерживает Long и Short как отдельные сетки;
- Grid Orders являются лимитными Entry orders;
- первый Entry привязан к Mark Price в момент запуска;
- трейдер задаёт уровни вручную;
- уровень можно задавать абсолютной ценой либо процентным расстоянием;
- Grid Geometry и Grid Sizing разделены;
- Long / Short allocation задаётся процентами;
- future qty рассчитывается системой из бюджета стороны, leverage и instrument limits;
- Martingale multiplier задаётся индивидуально на каждый ордер и умножает вес предыдущего уровня;
- factual filled volume immutable;
- pending/future qty может быть перераспределён;
- есть два ручных scope реструктуризации: `RECALCULATE_ORDER` и `RECALCULATE_GRID`;
- новые уровни можно добавлять в существующую сетку и после этого пересчитывать один уровень либо всю future часть;
- на Bybit одновременно поддерживается только заданное Active Order Window;
- один Grid Order может иметь несколько fills и остаётся одной логической единицей;
- TP строится от factual average fill и factual open qty конкретного StrategyLot;
- изменения конфигурации сохраняются как Grid Revision;
- внешние сигналы, технические индикаторы, новости, sentiment и AI price prediction не используются.

## Что ещё не формализовано полностью

- production-формула `capital_base` без двойного учёта PnL;
- автоматические triggers реструктуризации;
- автоматический reinvest;
- правила восстановления разгруженного объёма;
- полный rebase/trailing policy;
- Stop Loss;
- точные risk limits и emergency actions;
- autonomous strategy decisions.

## Архитектурное разделение

```text
Strategy Rules / Trader Configuration
        ↓
Grid Planner + Sizing Planner
        ↓
Restructuring Planner
        ↓
Risk Manager
        ↓
Execution Engine
        ↓
Bybit
```

Параллельно Recorder независимо фиксирует фактическую реальность Bybit.

- **Decision / Planning layer** формирует намерение и proposed changes.
- **Risk layer** проверяет допустимость.
- **Execution layer** механически исполняет утверждённый план.
- **Recorder** фиксирует, что реально произошло.

## Generated Grid

Подтверждённые Veles-like формулы Generated Grid не удаляются, но относятся к optional constructor. Они не должны ограничивать Manual Grid и не являются основной sizing-моделью стратегии.
