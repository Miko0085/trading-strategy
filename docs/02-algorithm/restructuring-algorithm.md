# Алгоритм реструктуризации сетки

**Статус: MANUAL RESTRUCTURING CONFIRMED / PROFIT-TAKING TRIGGER CONFIRMED / CAPITAL ROUTING OPEN**

Реструктуризация — planning layer. Она не отправляет команды на Bybit напрямую.

## 1. Главный приоритет

Цель реструктуризации — в первую очередь сохранять капитал, маржу и устойчивость позиции. Увеличение объёма ради прибыли не имеет приоритета над safety constraints.

## 2. Главный invariant

```text
Factual filled/open volume → immutable
Future/pending volume      → recalculable
```

Нельзя изменять историю фактических fills задним числом.

## 3. Входы

Используются:
- Mark Price;
- factual Long / Short position;
- StrategyLots;
- `filled_qty`, `open_qty`, average fill;
- wallet/equity/available margin и другие factual account fields;
- realized PnL / fees / funding;
- current Long/Short/Reserve allocation;
- pending Grid Orders;
- sizing mode стороны;
- `K` или `M_i`;
- leverage;
- актуальные Bybit instrument limits;
- current Grid Revision.

## 4. Триггеры

### Manual triggers

Подтверждены:

```text
RECALCULATE_ORDER
RECALCULATE_GRID
```

### Profit-taking trigger

Исполнение прибыльного TP/close является обязательным trigger для:

```text
refresh factual account state
→ recalculate available future budget
→ produce new Restructuring/Sizing Proposal
```

Это **не означает**, что система уже знает, куда именно должен пойти новый капитал. Routing между Long/Short остаётся OPEN.

## 5. RECALCULATE_ORDER

Трейдер выбирает конкретный future/partially-filled Grid Order.

Правила:
- factual `filled_qty/open_qty` не меняются;
- меняется только future remainder выбранного order;
- остальные levels не каскадируются автоматически;
- новый target должен помещаться в реально доступный future budget;
- результат проходит Bybit validation;
- создаётся новая Grid Revision/RestructuringEvent.

## 6. RECALCULATE_GRID

Пересчитывается вся eligible future часть выбранной стороны.

```text
Fresh factual account state
↓
Effective Side Budget
↓
- Factual Used Capital
↓
- Locked Future Capital
↓
Available Future Margin Budget
↓
× leverage
↓
Future Notional Budget
↓
Generate weights by selected sizing mode
↓
Normalize weights
↓
Calculate notional_i / qty_i
↓
Bybit hard validation
↓
RestructuringPlan
↓
Grid Revision
```

## 7. Sizing modes внутри restructuring

### POWER_CURVE

```text
raw_weight_i = (i/N)^K
```

`K` задаётся отдельно для Long и Short.

### PER_ORDER_M

```text
w1 = 1
w_i = w_(i-1) × M_i
```

Advanced mode. Каждый переход имеет собственный multiplier.

Другие Martingale modes в текущий MVP не входят.

## 8. Добавление нового Grid Order

После добавления нового level трейдер может:
- рассчитать только новый order;
- либо пересчитать всю eligible future Grid.

При полном пересчёте новый order участвует в текущем sizing mode.

## 9. Что именно перераспределяется

Реструктуризация не обязана возвращать прибыль в тот Grid Order, который её заработал.

Текущее подтверждённое направление — full-grid sizing как основной способ перераспределить future budget стороны.

При этом ещё OPEN:
- same-side reinvest;
- cross-side risk-priority reinvest;
- both-sides reinvest;
- точная доля/состав reinvestable capital.

## 10. Capital routing между Long и Short

Long и Short используют одну factual cross-margin reality, но могут иметь независимые logical budgets.

Возможные routing policies исследуются отдельно:

```text
A. Long profit  → Long future Grid
   Short profit → Short future Grid

B. New capital → side with higher risk/need

C. New capital → both sides by allocation policy
```

Ни одна из этих формул пока не утверждена как финальная.

## 11. Candidate risk-priority idea

Один из исследуемых факторов — положение Mark Price относительно factual LongAvg / ShortAvg.

Если Mark ближе к средней одной стороны, эта сторона потенциально может иметь больший safety-priority для будущего капитала.

Но одной distance-to-average недостаточно. Могут потребоваться:
- liquidation distance;
- margin utilization;
- available margin;
- current exposure;
- future pending exposure;
- reserve;
- влияние нового order на weighted average.

Статус: CANDIDATE.

## 12. Hard Safety Gate — атомарность плана

После любого расчёта проверяются:

```text
qty >= minOrderQty
qty aligned to qtyStep
notional >= minNotionalValue
price aligned to tickSize
```

Если хотя бы один обязательный order плана после нормализации невалиден:

```text
RESTRUCTURING_PLAN_INVALID
→ MANUAL_REVIEW
→ NO PARTIAL APPLY
→ NO AUTOMATIC CONTINUE
```

Execution/Planner не имеет права автоматически:
- увеличить qty за счёт Reserve;
- перенести капитал с другой стороны;
- пропустить невалидный order;
- изменить `K`, `M_i`, leverage или allocation;
- исполнить только валидную часть плана.

## 13. Factual Used Capital

Концептуально:

```text
AvailableFutureMarginBudget
= EffectiveSideBudget
- FactualUsedCapital
- LockedFutureCapital
```

Точная production-семантика `EffectiveSideBudget/capital_base` пока OPEN, чтобы исключить двойной учёт PnL/margin.

## 14. RestructuringPlan

Минимально:

```text
RestructuringPlan
- scope: ORDER | GRID
- side
- trigger
- target_order_id?
- source_revision
- factual_state_snapshot
- capital_snapshot
- sizing_mode
- power_k?
- per_order_m?
- effective_side_budget
- factual_used_capital
- locked_future_capital
- available_future_margin_budget
- future_notional_budget
- orders_before
- orders_after
- instrument_metadata_snapshot
- validation
- manual_review_reason?
- target_grid_revision
```

## 15. Pipeline

```text
Trigger / Manual Request
↓
Fresh State
↓
Sizing / Restructuring Proposal
↓
Hard Technical Validation
↓
Risk Manager
↓
ALLOW / MODIFY / DENY
↓
ApprovedExecutionPlan
↓
Execution Engine
↓
Bybit
```

В shadow/read-only режиме plan остаётся virtual.

## 16. Что OPEN

- production `capital_base`;
- reinvestable capital definition;
- Long/Short routing formula;
- cross-side safety priority;
- automatic rebase/trailing;
- recovery after TP;
- exact Risk Manager thresholds;
- automatic application policy after profit-taking trigger.
