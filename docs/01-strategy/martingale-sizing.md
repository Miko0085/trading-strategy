# Мартингейл и распределение объёма по Grid Orders

**Статус: CONFIRMED FUNCTIONAL SCOPE FOR MVP**

Эта страница описывает только **распределение future capital/notional между Grid Orders**.

Grid Geometry и Grid Sizing — независимые слои:

```text
Grid Geometry → где стоят Entry levels
Grid Sizing   → сколько капитала/notional/qty получает каждый level
```

## 1. Какие sizing modes нужны платформе

Для текущего функционала оставляем только два режима:

```text
POWER_CURVE
PER_ORDER_M
```

Остальные варианты (`LINEAR`, отдельный `GLOBAL_GEOMETRIC`, `EQUAL`, `MANUAL_WEIGHTS`, `REVERSE_GEOMETRIC`) не являются отдельными MVP modes и пока не нужны в интерфейсе.

Global geometric технически остаётся частным случаем `PER_ORDER_M`: если всем `M_i` задать одинаковое значение, получится обычная геометрическая прогрессия.

## 2. Общий принцип расчёта

Martingale/sizing применяется не напрямую к количеству монет, а к денежному размеру future position.

Канонический pipeline:

```text
Future Margin Budget B
× Leverage L
= Future Notional Budget N

N
→ sizing weights
→ normalized shares
→ notional_i
→ raw_qty_i = notional_i / entry_price_i
→ ROUND_DOWN by qtyStep
→ Bybit validation
```

Это важно, потому что одинаковый coin qty на разных Entry Price означает разный денежный размер позиции.

## 3. POWER_CURVE — степенное распределение объёма

`POWER_CURVE` — основной автоматический режим распределения объёма по всей стороне.

Трейдер задаёт один коэффициент `K` отдельно для Long и отдельно для Short.

Для `N` eligible future orders и порядкового номера `i = 1..N`:

```text
x_i = i / N
raw_weight_i = x_i ^ K
```

После этого:

```text
normalized_weight_i = raw_weight_i / Σ(raw_weight)
```

и:

```text
notional_i = FutureNotionalBudget × normalized_weight_i
```

### Смысл коэффициента K

- `K = 0` → все уровни имеют одинаковый raw weight;
- `0 < K < 1` → распределение более ровное, первые уровни получают относительно больше;
- `K = 1` → вес растёт линейно по номеру уровня;
- `K > 1` → капитал сильнее смещается к дальним уровням;
- чем выше `K`, тем круче рост future notional к глубоким Grid Orders.

Пример для `N=5`, `K=2`:

```text
raw weights:
#1 = (1/5)^2 = 0.04
#2 = (2/5)^2 = 0.16
#3 = (3/5)^2 = 0.36
#4 = (4/5)^2 = 0.64
#5 = (5/5)^2 = 1.00
```

После нормализации дальние уровни получают существенно большую долю future budget.

### Почему это не называем Logarithmic Martingale

Математически используется степенная функция `x^K`, а не логарифм.

Veles использует термин `Logarithmic Distribution` для управления распределением **ценовых уровней**. В нашей платформе `POWER_CURVE` применяет похожую идею управляемой кривизны к **sizing weights / объёму**, поэтому Price Geometry и Volume Sizing нельзя смешивать.

## 4. PER_ORDER_M — индивидуальный Martingale каждого Grid Order

`PER_ORDER_M` — advanced mode для максимального ручного контроля.

Первый уровень имеет базовый вес:

```text
w1 = 1
```

Для каждого следующего уровня трейдер задаёт собственный multiplier:

```text
w_i = w_(i-1) × M_i
```

Пример:

```text
M2 = 1.10
M3 = 1.40
M4 = 1.00
M5 = 1.80

w1 = 1.000
w2 = 1.100
w3 = 1.540
w4 = 1.540
w5 = 2.772
```

`M_i = 1.00` означает: на этом переходе Martingale-увеличения нет.

Это позволяет, например:
- почти не увеличивать первые Long levels;
- резко увеличить один глубокий Long order;
- использовать совершенно другую кривую для Short;
- выключить увеличение объёма на конкретном Grid Order без изменения остальных настроек.

## 5. Long и Short настраиваются независимо

Каждая сторона хранит собственный sizing config:

```text
Long:
  sizing_mode
  power_k?      # если POWER_CURVE
  per_order_m[] # если PER_ORDER_M

Short:
  sizing_mode
  power_k?
  per_order_m[]
```

Нельзя предполагать одинаковый Martingale для Long и Short.

## 6. Нормализация бюджета

После получения raw weights:

```text
W = Σw_i
share_i = w_i / W
```

Далее:

```text
margin_i = FutureMarginBudget × share_i
notional_i = margin_i × leverage
raw_qty_i = notional_i / entry_price_i
```

При одинаковом leverage математически эквивалентно сначала получить общий Future Notional Budget и распределить его по тем же shares.

## 7. Factual volume не участвует в перераспределении

Sizing engine распределяет только eligible future budget.

```text
filled_qty / open_qty = factual, immutable
remaining_entry_qty   = future, resizable
```

Перед полным перерасчётом:

```text
AvailableFutureBudget
= EffectiveSideBudget
- FactualUsedCapital
- LockedFutureCapital
```

Точная production-семантика `EffectiveSideBudget/capital_base` остаётся OPEN.

## 8. Перерасчёт при изменении капитала

При новом future budget веса рассчитываются заново выбранным mode.

Пример:

```text
Old Future Margin Budget = 1,000 USDT
New Future Margin Budget = 1,010 USDT
Leverage = 10x
```

Дополнительные `10 USDT` margin потенциально дают `100 USDT` additional notional, но платформа не должна просто добавлять `100` поверх старых orders вслепую.

Она пересчитывает весь актуальный eligible future budget через текущие weights и заново получает `notional_i / qty_i` для каждого pending order.

## 9. Profit-taking trigger

Исполнение прибыльного TP/close является trigger для обязательного обновления factual account state и нового sizing/restructuring proposal.

```text
Profitable TP
→ fresh account snapshot
→ recalculate future budget
→ apply selected sizing mode
→ validate full plan
```

Что именно становится новым reinvestable capital и в какую сторону оно маршрутизируется (same-side / cross-side / both) — отдельный OPEN вопрос и не относится к формуле Martingale.

## 10. Bybit hard validation

После расчёта каждого order:

```text
qty >= minOrderQty
qty aligned to qtyStep
notional >= minNotionalValue
price aligned to tickSize
```

Instrument limits загружаются из актуального Bybit instrument metadata.

Если хотя бы один обязательный order нового плана после нормализации невалиден:

```text
PLAN_INVALID
→ MANUAL_REVIEW
→ NO PARTIAL APPLY
```

Sizing engine не должен автоматически:
- увеличивать невалидный qty до минимума за счёт Reserve;
- переносить капитал с другой стороны;
- удалять невалидный level и продолжать остальные;
- менять `K`, `M_i` или allocation, чтобы искусственно пройти validation.

## 11. Что должно быть в UI

### Side-level settings

Для каждой стороны отдельно:
- `Sizing Mode`: `Power Curve` / `Per-Order M`;
- `K` при Power Curve;
- Future Margin Budget / Future Notional Budget preview;
- суммарный planned margin/notional;
- validation state.

### Grid Order

Для каждого order:
- Entry Price;
- calculated raw/normalized weight;
- planned margin;
- planned notional;
- calculated qty;
- factual filled/open qty;
- Bybit validation;
- `M_i` только в advanced `PER_ORDER_M` mode.

## 12. Что специально не добавляем сейчас

Не нужны отдельные MVP modes:
- Linear/Arithmetic Martingale;
- Equal/DCA sizing;
- отдельный Global Geometric mode;
- Reverse Martingale;
- arbitrary manual weight entry.

При появлении подтверждённой необходимости их можно добавить позже без изменения общего normalization pipeline.
