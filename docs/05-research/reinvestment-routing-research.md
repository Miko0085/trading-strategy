# Исследование маршрутизации реинвеста и автоматической реструктуризации

**Статус: TRIGGER CONFIRMED / ROUTING OPEN**

Документ фиксирует то, что уже подтверждено, и отделяет это от нерешённой маршрутизации капитала между Long и Short.

## Что уже подтверждено

Первый приоритет — сохранить капитал, маржу и позиции.

Profit-taking event является trigger:

```text
profitable TP / profitable close
↓
fresh factual account state
↓
recalculate future budget
↓
new sizing / restructuring proposal
```

Factual filled/open volume не меняется.

## Что пока НЕ подтверждено

Trigger не определяет автоматически:
- что именно считать reinvestable capital;
- какая сторона получает новый capital;
- можно ли временно менять Long/Short allocation;
- должен ли proposal применяться автоматически после Risk Check.

## Cross Margin и logical budgets

Long и Short используют общую factual cross-margin reality, но platform должна отдельно видеть:

```text
Account Cross-Margin State
        ↓
Strategy Capital State
        ↓
Long Future Budget
Short Future Budget
Reserve
```

## Candidate A — Same-Side

```text
Long profit  → Long future Grid
Short profit → Short future Grid
```

Самый простой и объяснимый routing. Статус: CANDIDATE.

## Candidate B — Risk-Priority Cross-Side

Capital направляется стороне, где он сильнее снижает текущий risk.

Исследуемые inputs:
- Mark distance to LongAvg / ShortAvg;
- liquidation distance;
- used margin;
- available margin;
- allocation utilization;
- current exposure;
- future pending exposure;
- reserve;
- effect of proposed entries on weighted average.

Статус: CANDIDATE.

## Candidate C — Both Sides

Capital делится между Long и Short по allocation/routing policy.

Риск — fragmentation: после деления некоторые orders могут стать меньше exchange minimum.

Статус: CANDIDATE.

## Full-grid restructuring — preferred direction

Reinvest не обязан возвращаться в тот Grid Order, который заработал profit.

Основное направление:

```text
new side budget
- factual used capital
- locked future capital
= available future margin budget

→ selected sizing mode
→ new weights
→ new qty all eligible pending orders
```

Поддерживаются только два текущих sizing mode:
- `POWER_CURVE`;
- `PER_ORDER_M`.

## Hard Safety Gate

Если хотя бы один mandatory order не проходит актуальные Bybit limits:

```text
PLAN_INVALID
→ MANUAL_REVIEW
→ NO PARTIAL APPLY
```

Проверяются минимум:
- `minOrderQty`;
- `qtyStep`;
- `minNotionalValue`;
- `tickSize`.

## Minimum-capital implication

Если reinvestment слишком мал для технически валидного перераспределения по выбранной стороне/сетке, система не должна искусственно увеличивать qty или расходовать Reserve.

Это может привести к `MANUAL_REVIEW` или ожиданию следующего capital event — точная policy ещё OPEN.

## Что исследовать дальше

1. net realized profit или released capital + profit?
2. same-side / risk-priority / both-side?
3. какая формула risk priority?
4. сохраняется ли базовый allocation?
5. что делать при capital, достаточном только для одной стороны?
6. automatic apply или proposal-only после Risk Check?
7. cooldown/debounce серии TP triggers?
8. как маршрутизация влияет на liquidation distance и weighted averages?
