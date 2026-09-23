# Механика сетки

**Статус: ПОДТВЕРЖДЁННАЯ БАЗОВАЯ МЕХАНИКА / MANUAL GRID PRIMARY / GENERATED GRID OPTIONAL**

## 1. Основной режим текущего MVP

Текущий основной workflow — ручная настройка Grid Geometry с автоматическим расчётом будущего объёма.

```text
Trader sets levels
→ Capital Allocation
→ Per-Order Martingale Chain
→ Automatic Future Qty
→ Active Order Window
→ Execution
→ Factual Fills
→ Manual Volume Restructuring
```

Generated Grid сохраняется как дополнительный конструктор и не является основным способом работы трейдера.

## 2. Grid Order

Grid Order — логический лимитный Entry-уровень Long или Short.

Каждый уровень является отдельной настраиваемой единицей и может иметь собственные:
- Entry Price / offset;
- per-order Martingale multiplier;
- TP Steps;
- note;
- runtime/factual state после fills.

## 3. Первый ордер и startup offset

При запуске стратегии фиксируется текущая Mark Price.

Для первого уровня:
- Long располагается ниже Mark Price;
- Short располагается выше Mark Price.

Трейдер задаёт startup offset, после чего система получает фактическую цену первого Entry с учётом `tickSize`.

## 4. Manual Grid Geometry

Трейдер самостоятельно определяет, где должны находиться уровни.

Для уровня допускаются два способа задания intent:

### Absolute Price

Трейдер задаёт желаемую Entry Price напрямую.

### Percentage Spacing

- #1: процент относительно reference/Mark Price;
- #2+: процент относительно предыдущего логического уровня.

Цена и процент являются двумя представлениями одной геометрии. Система не должна автоматически заменять вручную заданную геометрию Veles-like распределением.

## 5. Grid Geometry и Grid Sizing независимы

```text
Grid Geometry
→ цены и расстояния между уровнями

Grid Sizing
→ распределение будущего капитала и qty
```

Перерасчёт объёма не должен автоматически менять цены уровней.

## 6. Capital Allocation

Для Long и Short задаётся собственная доля капитала. Reserve остаётся отдельной защищённой долей.

На момент перерасчёта система использует свежий factual account state и определяет бюджет стороны.

```text
Side Budget
- Factual Used Capital
- Locked Future Capital
= Available Future Budget
```

Точная production-семантика `capital_base` ведётся отдельно; нельзя допускать двойного учёта PnL.

## 7. Per-Order Martingale

В Manual Grid нет одного глобального Martingale multiplier, который автоматически строит `M^i` для всех уровней.

У каждого уровня начиная со второго есть свой multiplier относительно предыдущего веса:

```text
w1 = 1
w2 = w1 × M2
w3 = w2 × M3
...
wn = w(n-1) × Mn
```

Пример:

```text
#1 weight = 1.00
#2 M2 = 1.20 → weight = 1.20
#3 M3 = 1.50 → weight = 1.80
#4 M4 = 1.10 → weight = 1.98
```

Эти cumulative weights задают относительное распределение future budget.

## 8. Automatic Future Qty

После того как цены и Martingale chain заданы, система рассчитывает qty.

Концептуально:

```text
normalized_weight_i = weight_i / Σ eligible_weights
level_margin_budget_i = AvailableFutureBudget × normalized_weight_i
planned_notional_i = level_margin_budget_i × leverage
raw_future_qty_i = planned_notional_i / entry_price_i
```

После этого qty нормализуется `ROUND_DOWN` по `qtyStep` и проходит проверки Bybit `minOrderQty` и `minNotionalValue`.

Фактический `configured_qty` может состоять из:

```text
configured_qty = filled_qty + remaining_entry_qty
```

## 9. Factual volume immutable

После fill уже исполненный объём нельзя перераспределить между уровнями.

```text
filled_qty → factual history
open_qty   → factual exposure
remaining_entry_qty → future intent, может быть пересчитан
```

Partial fill не превращает один Grid Order в несколько логических уровней.

## 10. Manual Volume Restructuring

Поддерживаются два ручных scope.

### RECALCULATE_ORDER

Пересчитывается только future qty выбранного ордера.

Это действие не должно автоматически каскадировать изменение на последующие уровни. Оно обязано проверить, хватает ли свободного future budget.

### RECALCULATE_GRID

Пересчитывается вся eligible future часть стороны:

```text
fresh factual state
→ side budget
→ subtract factual used capital
→ subtract locked future capital
→ rebuild cumulative per-order weights
→ normalize remaining future budget
→ calculate new pending qty
→ Grid Revision
```

## 11. Добавление новых уровней

Трейдер может добавить #6, #7, #8 и далее в уже существующую логическую сетку.

После добавления нового уровня доступны два действия:
- рассчитать future qty только нового уровня;
- перераспределить future budget всей оставшейся сетки.

Исполненные части существующих ордеров остаются неизменными.

## 12. Active Order Window

Полная логическая сетка может иметь любое разрешённое число уровней, но на Bybit одновременно находится только заданное количество Entry orders.

Пример:

```text
Logical Grid: #1 ... #10
Active Order Window = 3

Bybit: #1 #2 #3
#1 filled
→ activate #4
```

Точный runtime trigger partial/full replacement ведётся как execution policy, но сама модель Active Window подтверждена.

## 13. Take Profit

После первого factual fill появляется StrategyLot / Filled Allocation.

TP считается от:
- factual average fill;
- factual open qty.

Неисполненная часть Entry не участвует в TP.

## 14. Generated Grid — optional constructor

Старый Veles-like constructor сохраняется в коде как дополнительная функция.

Для него по-прежнему известна normalized power distribution:

```text
P_i = P1 - (P1 - PN) × ((i - 1)/(N - 1))^K
```

и legacy/global geometric martingale:

```text
w_i = M^(i-1)
```

Но эти формулы относятся только к Generated Grid и не должны ограничивать или определять Manual Grid.

## 15. Что пока остаётся OPEN

- автоматические triggers перерасчёта;
- automatic recovery после TP;
- точная production-формула capital_base;
- правила автоматического reinvest;
- полный rebase/trailing policy;
- autonomous restructuring decisions.
