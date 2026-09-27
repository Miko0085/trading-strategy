# Будущий Risk Manager

**Статус: FUTURE / INDEPENDENT SAFETY GATE**

Risk Manager — отдельный слой между Planning и Execution.

## Главный принцип

Первый приоритет — сохранить капитал, маржу и позиции. Risk Manager не максимизирует прибыль и не прогнозирует рынок.

## Контракт

```text
Strategy / Restructuring Planner
        ↓
Proposed Plan
        ↓
Technical Execution Validation
        ↓
Risk Manager
        ↓
ALLOW / MODIFY / DENY
        ↓
Approved Execution Plan
        ↓
Execution Engine
```

Technical Bybit validation и Risk Manager — разные уровни:
- `minOrderQty`, `qtyStep`, `minNotionalValue`, `tickSize` — hard technical gate;
- exposure/margin/liquidation/reserve — risk gate.

Если technical plan invalid, он вообще не должен доходить до обычного ALLOW flow.

## Что Risk Manager потенциально проверяет

- equity;
- available margin;
- reserve;
- Long / Short exposure;
- gross/net exposure;
- allocation utilization;
- leverage;
- liquidation distance;
- effect of proposed orders on weighted average;
- concentration per symbol;
- total future pending notional;
- capital budget;
- stress under adverse price movement.

## Sizing-aware risk

Risk Manager должен видеть не только coin qty, но и:
- sizing mode;
- `K`;
- per-order `M_i`;
- margin_i;
- notional_i;
- cumulative future exposure.

Высокий `K` или отдельный большой `M_i` не запрещён сам по себе, но может привести к DENY/MODIFY из-за итоговой экспозиции.

## Результаты

### ALLOW

План допустим без изменений.

### MODIFY

Risk Manager может предложить ограничение параметров только по заранее подтверждённым правилам. Он не должен сам придумывать новую Grid Geometry или routing capital.

### DENY

Plan не передаётся в Execution Engine.

## Emergency actions

Только после отдельной формализации:
- block new entries;
- freeze restructuring;
- reduce exposure;
- early unload;
- emergency close.

## Что пока OPEN

- минимальный reserve;
- допустимый liquidation distance;
- limits на gross exposure;
- limits на side allocation;
- rules ALLOW/MODIFY/DENY;
- emergency actions;
- cross-side capital priority.

## Risk Manager не прогнозирует рынок

Он отвечает:

> Допустим ли proposed plan при текущем factual состоянии капитала, позиций и биржевых ограничений?

Новости, sentiment, technical indicators и AI price prediction не используются.
