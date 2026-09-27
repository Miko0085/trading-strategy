# Механика сетки

**Статус: MANUAL GRID PRIMARY / AUTONOMOUS ORDERS / TWO SIZING MODES**

## 1. Основной workflow

```text
Trader sets Long / Short geometry
→ choose sizing mode per side
   - POWER_CURVE
   - PER_ORDER_M
→ calculate future budget/notional
→ calculate qty per order
→ validate all Bybit limits
→ Active Order Window
→ Execution
→ Factual Fills
→ TP1..TP4
→ profit-taking trigger
→ restructuring proposal
```

Generated Grid остаётся legacy/optional и не является основным блоком UI.

## 2. Grid Order — автономная сущность

Каждый Grid Order может иметь собственные:
- Entry Price / offset;
- `M_i` в advanced `PER_ORDER_M` mode;
- planned margin/notional/qty;
- factual fills и own average fill;
- до четырёх TP parts;
- note / lock / revision history.

Long и Short не обязаны использовать одинаковые параметры.

## 3. Manual Grid Geometry

Первый Entry привязан к reference Mark Price:
- Long ниже Mark Price;
- Short выше Mark Price.

Трейдер может задавать уровень:
- абсолютной ценой;
- процентным spacing.

Для #2+ процент относится к предыдущему логическому уровню.

## 4. Geometry и Sizing независимы

```text
Geometry → цены
Sizing   → денежный вес и qty
```

Изменение budget, Martingale или restructuring не должно само по себе передвигать Entry Price.

Trailing/rebase — отдельная будущая политика.

## 5. Capital Allocation

Long/Short/Reserve задаются отдельно.

Перед sizing:

```text
AvailableFutureMarginBudget
= EffectiveSideBudget
- FactualUsedCapital
- LockedFutureCapital
```

Production semantics `EffectiveSideBudget/capital_base` пока OPEN.

## 6. Sizing Mode: POWER_CURVE

Для `N` eligible future orders:

```text
x_i = i / N
raw_weight_i = x_i ^ K
```

Затем веса нормализуются на 100% future budget.

`K` задаётся отдельно для Long и Short.

Чем выше `K`, тем сильнее planned capital смещается к дальним уровням.

## 7. Sizing Mode: PER_ORDER_M

Advanced mode:

```text
w1 = 1
w_i = w_(i-1) × M_i
```

Каждый Grid Order начиная со второго имеет собственный multiplier.

`M_i = 1` означает отсутствие увеличения веса на конкретном переходе.

Global geometric не нужен как отдельный режим: одинаковые `M_i` воспроизводят его автоматически.

## 8. Automatic Future Qty

После генерации raw weights:

```text
share_i = weight_i / Σweights
margin_i = AvailableFutureMarginBudget × share_i
notional_i = margin_i × leverage
raw_qty_i = notional_i / entry_price_i
```

Далее:

```text
qty_i = ROUND_DOWN_TO_QTY_STEP(raw_qty_i)
```

и выполняется hard validation Bybit.

## 9. Minimum-lot safety gate

Перед стартом Grid и после каждого sizing/restructuring:

```text
qty >= minOrderQty
qty aligned to qtyStep
notional >= minNotionalValue
price aligned to tickSize
```

Если любой обязательный order плана не проходит limits:

```text
PLAN_INVALID
→ MANUAL_REVIEW
→ NO PARTIAL APPLY
```

Нельзя автоматически поднимать qty до минимума, забирать Reserve, пропускать order или менять weights.

## 10. Factual volume immutable

```text
filled_qty / open_qty → factual
remaining_entry_qty   → future intent
```

`configured_qty` после restructuring всегда должен удовлетворять:

```text
configured_qty = filled_qty + remaining_entry_qty
configured_qty >= filled_qty
```

## 11. Active Order Window

Полная логическая Grid может содержать больше levels, чем фактически выставлено на Bybit.

Пример:

```text
Logical Grid: #1..#10
Active Window = 3
Bybit: #1 #2 #3
```

По мере исполнения активируются следующие queued levels согласно execution policy.

## 12. Take Profit

После первого fill появляется StrategyLot.

Для одного StrategyLot:
- максимум TP1..TP4;
- TP считается от factual average fill;
- closing qty считается от factual open qty;
- суммарный TP qty не может превышать factual open qty.

## 13. Profit-taking как trigger

Исполнение прибыльного TP/close обязательно инициирует:
- refresh factual account state;
- новый расчёт future budget;
- новый restructuring proposal.

Маршрутизация капитала между Long/Short остаётся OPEN.

## 14. Manual restructuring

Поддерживаются:

```text
RECALCULATE_ORDER
RECALCULATE_GRID
```

### RECALCULATE_ORDER

Меняет future intent только выбранного order и не каскадирует остальные автоматически.

### RECALCULATE_GRID

Пересчитывает всю eligible future часть выбранной стороны текущим sizing mode.

## 15. Generated Grid

Legacy Generated Grid может оставаться в коде для исследований/совместимости, но:
- не является primary workflow;
- не должен быть главным planning block UI;
- его price distribution не должна автоматически заменять Manual Geometry.

## 16. OPEN

- `capital_base`;
- reinvestment routing Long/Short;
- cross-side risk priority;
- trailing/rebase;
- recovery after TP;
- production Risk Manager thresholds.
