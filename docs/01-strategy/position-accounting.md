# Position Accounting

**Статус: CONFIRMED (единица объёма) / FUTURE (lot-модель)**

## CONFIRMED RULE — единица объёма

**PRIMARY SIZE UNIT = COIN QUANTITY.**

Долларовая маржа не используется как primary size.

### Пример

```
Order #1
original_qty = 1000 LSK

TP: close 25%
→ close_qty = 250 LSK
```

Производные величины (считаются из coin quantity, не наоборот):

- USDT notional;
- margin;
- PnL.

## Strategy Lot vs Bybit position

Bybit агрегирует все исполнения по символу/стороне в одну Long или одну Short позицию (одна average price, один size). Внутренняя логика стратегии должна сохранять **отдельные Strategy Lots**:

```
LONG POSITION (Bybit: один агрегат)

  Lot #1
    source_order
    actual_average_execution_price
    original_qty
    remaining_qty
    closed_qty
    TP configuration

  Lot #2
    ...

  Lot #N
    ...
```

Средняя цена всей позиции по Bybit **не заменяет** цену конкретного lot — TP считается от цены lot (см. [partial-take-profit.md](partial-take-profit.md)).

## Статус реализации

Lot-модель — `FUTURE`: сейчас Recorder хранит только то, что видит на бирже (агрегированную позицию, ордера, исполнения) — см. [04-platform/data-model.md](../04-platform/data-model.md). Отдельного хранилища Strategy Lot в системе пока нет; это требование к будущей platform-логике, не к Recorder'у.
