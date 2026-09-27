# Обзор стратегии

**Статус: ПОДТВЕРЖДЁННАЯ БАЗОВАЯ МЕХАНИКА + ОТКРЫТАЯ МАРШРУТИЗАЦИЯ РЕИНВЕСТА**

## Главный принцип

Первый приоритет стратегии — сохранить капитал, маржу и позиции. Улучшение average price, hedge structure и прибыльность происходят после safety checks.

## Текущий основной workflow

```text
Trader Configuration
→ Manual Long / Short Grid Geometry
→ Side Capital Allocation
→ Sizing Mode
   - POWER_CURVE
   - PER_ORDER_M [advanced]
→ Automatic Future Qty
→ Bybit Instrument Validation
→ Active Order Window
→ Execution
→ Factual Fills / StrategyLots
→ TP1..TP4
→ Profit-taking Trigger
→ Restructuring Proposal
```

Generated Grid/Veles-like constructor остаётся legacy/optional и не является основным UI/workflow.

## Long и Short

Long и Short — независимые стороны Hedge Mode. У них могут отличаться:
- allocation;
- leverage;
- geometry;
- sizing mode;
- Power Curve `K`;
- per-order `M_i`;
- Active Order Window;
- TP configuration;
- risk constraints.

Каждый Grid Order также является автономной сущностью со своей factual history.

## Подтверждённая механика

- Manual Grid — основной режим;
- Entry задаётся абсолютной ценой или процентным spacing;
- Geometry и Sizing независимы;
- qty рассчитывается системой из future budget, leverage, sizing weights и Entry Price;
- sizing применяется к margin/notional, а не напрямую к coin qty;
- для MVP нужны два sizing mode: `POWER_CURVE` и `PER_ORDER_M`;
- `POWER_CURVE` автоматически формирует веса всей стороны по коэффициенту `K`;
- `PER_ORDER_M` позволяет каждому переходу Grid Order иметь свой multiplier; `M_i=1` означает отсутствие увеличения на этом шаге;
- factual fills immutable;
- pending/future qty может пересчитываться;
- один Grid Order может иметь несколько fills;
- StrategyLot появляется после первого fill;
- максимум четыре TP parts на StrategyLot;
- profitable TP/close является trigger для нового расчёта/restructuring proposal;
- Active Order Window ограничивает число фактических Entry orders на Bybit;
- существенные изменения intent создают Grid Revision.

## Sizing pipeline

```text
Future Margin Budget
× leverage
= Future Notional Budget

Future Notional Budget
× normalized sizing weights
= notional_i

qty_i = notional_i / entry_price_i
```

После этого qty/price проходят Bybit normalization и hard validation.

## Hard execution rule

Если хотя бы один обязательный order нового плана не проходит актуальные `minOrderQty`, `qtyStep`, `minNotionalValue` или `tickSize`, план не применяется частично:

```text
INVALID PLAN
→ MANUAL_REVIEW
→ NO PARTIAL APPLY
```

## Что ещё OPEN

- точная production-формула `capital_base`;
- что именно считается reinvestable capital: net realized profit или released capital + profit;
- маршрутизация reinvestment между Long / Short / обеими сторонами;
- автоматический cross-side priority;
- recovery/rebase/trailing rules;
- точные Risk Manager limits;
- Stop Loss / emergency exit policy.

## Архитектурное разделение

```text
Strategy / Configuration
        ↓
Sizing + Restructuring Planner
        ↓
Risk Manager
        ↓
Execution Engine
        ↓
Bybit

Bybit → Recorder → Research/Reconciliation
```

Recorder остаётся независимо read-only.
