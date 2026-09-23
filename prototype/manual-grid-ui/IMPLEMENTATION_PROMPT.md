# Manual Grid UI MVP — актуальное ТЗ реализации

## Цель

Создать рабочий интерфейс управления Manual Long Grid и Manual Short Grid, где трейдер вручную задаёт геометрию уровней, а система автоматически рассчитывает future qty из доступного бюджета стороны.

Основной MVP больше не строится вокруг Veles-like Generated Grid.

Generated Grid остаётся в коде как дополнительный/legacy constructor и не должен определять основной пользовательский flow.

## Архитектурные ограничения

- Recorder (`src/recorder/`) остаётся permanently read-only.
- Новый operational UI/backend остаётся в `prototype/manual-grid-ui/`.
- До отдельного решения не добавлять production Bybit write actions.
- Все реальные fills/positions/orders считаются factual truth.
- Planned qty нельзя смешивать с factual execution.
- Внешние новости, sentiment, индикаторы и AI price prediction запрещены как вход стратегии.

## Основной пользовательский flow

```text
Выбрать symbol
↓
Получить factual Bybit account state
↓
Задать Long / Short / Reserve allocation
↓
Настроить Manual Long Grid / Manual Short Grid
↓
Для каждого уровня задать Entry Price или % spacing
↓
Для каждого уровня задать per-order Martingale multiplier
↓
Рассчитать future qty автоматически
↓
Проверить Bybit limits и allocation
↓
Настроить Active Order Window
↓
Сохранить Grid Revision
↓
После factual fills учитывать исполненный объём отдельно
↓
По кнопке выполнить RECALCULATE_ORDER или RECALCULATE_GRID
```

## Интерфейс

Весь UI — на русском.

Desktop сохраняет одновременное отображение Long и Short. На мобильном допускается компактное переключение представления, если это не меняет доменную модель.

## Верхняя панель

Показывать:
- symbol;
- Mark Price;
- wallet balance / equity;
- available margin;
- factual Long / Short position;
- position mode;
- timestamp обновления;
- Bybit connection status.

## Capital Allocation

Трейдер задаёт:
- Long %;
- Short %;
- Reserve %.

Сумма не должна превышать 100%.

Для каждого перерасчёта backend получает свежий factual account state и определяет Effective Side Budget.

Точная production-семантика `capital_base` должна оставаться изолированной в CapitalSnapshot/Calculator и не должна выдумываться во frontend.

## Manual Grid Geometry

Основной экран Long/Short содержит список Grid Orders.

Трейдер может:
- добавить новый уровень кнопкой `+ Добавить ордер`;
- удалить future level, если это не противоречит factual state;
- менять порядок/номер только безопасным способом;
- задавать Entry двумя способами.

### PRICE

Трейдер вводит абсолютную Entry Price.

### PERCENT

Для #1:
- `Отступ от текущей цены, %`.

Для #2+:
- `Отступ от предыдущего ордера, %`.

UI должен показывать оба представления, но хранить явный `entry_input_mode`, чтобы не было неявной подмены пользовательского intent.

## Startup Offset

При запуске/подготовке Grid фиксируется reference Mark Price.

- Long #1 должен быть ниже reference Mark Price.
- Short #1 должен быть выше reference Mark Price.

Если пользователь вводит некорректную direction price, показать validation error.

## Per-Order Martingale

У каждого Grid Order начиная со второго есть собственный `martingale_multiplier`.

Семантика:

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
#2 M = 1.20 → 1.20
#3 M = 1.50 → 1.80
```

В карточке ордера показывать:
- Martingale multiplier;
- resulting cumulative weight;
- planned/future qty после расчёта.

Не использовать глобальный `M^i` как основную Manual Grid sizing-модель.

## Automatic Future Sizing

Трейдер не обязан вручную вводить qty каждого уровня.

Backend рассчитывает future qty.

Концептуальный pipeline:

```text
Effective Side Budget
- Factual Used Capital
- Locked Future Capital
= Available Future Budget

Per-Order Martingale Chain
→ normalized eligible weights
→ margin budget per level
→ notional using leverage
→ raw coin qty using entry price
→ ROUND_DOWN by qtyStep
→ minOrderQty/minNotional validation
```

Для каждого уровня хранить отдельно:
- `configured_qty`;
- `filled_qty`;
- `remaining_entry_qty`;
- `open_qty`;
- `closed_qty`.

Invariant:

```text
configured_qty >= filled_qty
configured_qty = filled_qty + remaining_entry_qty
```

## Factual Used Capital

При любом перерасчёте backend обязан учитывать уже исполненный factual volume.

Исполненная позиция не может быть отменена математическим перерасчётом.

Factual used capital вычисляется только из factual attributed open exposure согласно подтверждённой capital semantics backend.

## Active Order Window

Трейдер задаёт число одновременно активных Entry Orders для Long и Short независимо.

Пример:

```text
Grid = 10 levels
Active Window = 3

Bybit future execution intent:
#1 #2 #3 active
#4 ... #10 queued
```

При освобождении слота Execution Engine позже активирует следующий queued level.

До подключения write adapter UI показывает planned/virtual state.

## Manual Volume Restructuring

Нужно реализовать два отдельных действия.

### 1. RECALCULATE_ORDER

Кнопка на карточке каждого future/partially future Grid Order:

`Пересчитать объём`

Поведение:
- получить свежий factual state;
- сохранить factual filled/open qty;
- рассчитать допустимый future qty выбранного уровня;
- не менять автоматически остальные уровни;
- проверить remaining side budget;
- показать before/after;
- после подтверждения создать новую Grid Revision.

Важно: изменение Martingale этого уровня не должно автоматически каскадировать следующие уровни в режиме `RECALCULATE_ORDER`.

### 2. RECALCULATE_GRID

Кнопка на уровне всей Long/Short стороны:

`Перераспределить объём всей сетки`

Поведение:
- fresh factual account state;
- пересчитать Effective Side Budget;
- вычесть factual used capital;
- вычесть locked future capital;
- построить cumulative Martingale chain;
- перераспределить available future budget между всеми eligible pending levels;
- factual fills не менять;
- показать before/after diff;
- создать новую Grid Revision после подтверждения.

## Добавление нового ордера

После `+ Добавить ордер` новый уровень появляется без выдуманного factual state.

Трейдер может выбрать:
- `Рассчитать этот ордер`;
- `Перераспределить всю сетку`.

Второй вариант включает новый уровень в cumulative Martingale chain.

## Partial Fill

Один Grid Order может иметь несколько Bybit executions.

После первого fill:
- `filled_qty` увеличивается;
- StrategyLot создаётся/обновляется;
- actual average fill пересчитывается;
- factual open qty становится immutable для sizing;
- только remaining Entry qty остаётся future intent.

## Take Profit

Для каждого Grid Order / StrategyLot разрешить несколько TP steps.

TP factual volume основывается на:
- actual average fill;
- factual open qty.

Если Entry ещё не исполнен, UI может показывать planned TP preview, но должен явно отличать его от factual TP.

Обычный TP — limit order в будущей execution integration.

## Generated Grid

Текущий Generated Grid code не удалять.

Но в основном UI его можно:
- скрыть;
- перенести в secondary/advanced block;
- пометить как дополнительный constructor.

Подтверждённые формулы Generated Grid остаются отдельными:

```text
Normalized Power Distribution
P_i = P1 - (P1 - PN) × ((i - 1)/(N - 1))^K

Legacy/global generated martingale
w_i = M^(i-1)
```

Они не должны автоматически применяться к Manual Grid.

## Revision / Audit

Любое существенное изменение должно сохранять:
- source revision;
- action;
- scope;
- before;
- after;
- factual snapshot id/context;
- timestamp;
- validation result.

Для restructuring action дополнительно:

```text
scope = ORDER | GRID
target_order_id?
reason = MANUAL_RECALCULATION
```

## Generated / Manual / Factual sources

UI и backend должны явно различать:
- MANUAL_INTENT;
- GENERATED_INTENT;
- ALGORITHM_SIZING;
- MANUAL_OVERRIDE;
- FACTUAL_EXECUTION.

## Backend responsibilities

Calculation/Sizing service должен быть deterministic/pure там, где возможно.

Минимальные функции:
- entry price/offset conversion;
- cumulative per-order weights;
- side budget calculation;
- factual used capital calculation;
- available future budget;
- qty allocation;
- instrument normalization;
- weighted average fill;
- TP calculations;
- RECALCULATE_ORDER plan;
- RECALCULATE_GRID plan;
- validation and diff.

Использовать `Decimal`, не binary float, для финансовой математики backend.

## Не реализовывать сейчас автоматически

- automatic restructuring triggers;
- automatic recovery;
- automatic reinvest triggers;
- automatic rebase;
- autonomous trailing decision;
- AI trading decisions;
- news/signals/indicators;
- production Bybit write actions без отдельного решения;
- autonomous Risk Manager.

## Обязательные тесты

### Geometry
- Long #1 below Mark;
- Short #1 above Mark;
- PRICE mode;
- PERCENT mode;
- sequential percentage chain;
- wrong direction validation.

### Martingale
- per-order cumulative weights;
- `1 → ×1.2 → ×1.5 = 1.8`;
- изменение M влияет на downstream chain при full-grid calculation;
- global Generated Grid M не смешивается с Manual Grid M.

### Sizing
- side budget allocation;
- factual used capital subtraction;
- locked future subtraction;
- qty rounding down;
- minOrderQty/minNotional validation;
- reserve protection.

### Restructuring
- RECALCULATE_ORDER меняет только target future qty;
- остальные orders не меняются;
- RECALCULATE_GRID перераспределяет eligible future qty;
- filled_qty immutable;
- partially filled order сохраняет factual part;
- новый уровень входит в full-grid recalculation;
- before/after audit;
- revision created.

### Active Window
- logical grid > active window;
- queued levels не считаются factual exchange orders;
- next activation candidate определяется корректно.

### Safety
- backend read-only Bybit guard сохраняется;
- no production write method;
- no external signals.

## Definition of Done текущего этапа

MVP этап считается готовым, когда трейдер может:
1. выбрать актив;
2. увидеть factual Bybit state;
3. задать Long/Short/Reserve allocation;
4. вручную построить Long и Short grid;
5. задать каждый уровень ценой или процентом;
6. задать per-order Martingale;
7. автоматически получить qty по каждому future order;
8. увидеть factual vs future volume отдельно;
9. настроить Active Order Window;
10. добавить новый уровень;
11. пересчитать только выбранный ордер;
12. перераспределить future volume всей сетки;
13. сохранить immutable Grid Revision;
14. увидеть before/after history;
15. не изменять factual fills при любом sizing recalculation;
16. не отправлять production trade actions из текущего read-only/shadow MVP.
