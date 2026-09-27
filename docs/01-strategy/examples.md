# Примеры механики

Все примеры синтетические и не являются универсальными торговыми правилами.

## Пример 1 — Manual Long Grid

```text
Mark Price = 100

#1 Entry = 90
#2 Entry = 85
#3 Entry = 78
#4 Entry = 70
```

Geometry задана трейдером. Sizing считается отдельно.

## Пример 2 — Power Curve sizing

Пусть:

```text
Future Margin Budget = 100 USDT
Leverage = 10x
Future Notional Budget = 1,000 USDT
N = 4
K = 2
```

Raw weights:

```text
#1 = (1/4)^2 = 0.0625
#2 = (2/4)^2 = 0.25
#3 = (3/4)^2 = 0.5625
#4 = (4/4)^2 = 1.00
```

После нормализации дальние levels получают большую долю notional.

Coin qty каждого уровня затем рассчитывается отдельно:

```text
qty_i = notional_i / entry_price_i
```

## Пример 3 — Per-Order M

```text
M2 = 1.10
M3 = 1.50
M4 = 1.00

w1 = 1.00
w2 = 1.10
w3 = 1.65
w4 = 1.65
```

На переходе #3→#4 увеличение веса выключено через `M4=1.00`.

## Пример 4 — один Grid Order исполнился несколькими fills

```text
configured_qty = 1000

Fill #1 = 300
Fill #2 = 400
Fill #3 = 300
```

После первого Fill уже существует StrategyLot/Filled Allocation.

После всех fills:

```text
filled_qty = 1000
remaining_entry_qty = 0
```

Это по-прежнему один Grid Order.

## Пример 5 — partial fill + restructuring

```text
configured_qty = 1000
filled_qty = 300
remaining_entry_qty = 700
```

После нового sizing system может определить:

```text
new remaining_entry_qty = 500
```

Тогда:

```text
configured_qty = 300 + 500 = 800
```

Factual `filled_qty=300` не изменяется.

## Пример 6 — максимум четыре TP parts

```text
open_qty = 1000

TP1 = close 30%
TP2 = close 25%
TP3 = close 25%
TP4 = close 20%
```

Доли могут быть другими, но TP parts не больше четырёх, а суммарный close qty не превышает factual open qty.

## Пример 7 — биржевой минимум блокирует весь план

Если после sizing:

```text
Order #4 qty < minOrderQty
```

то нельзя просто пропустить #4 и отправить остальные.

```text
PLAN_INVALID
→ MANUAL_REVIEW
→ NO PARTIAL APPLY
```
