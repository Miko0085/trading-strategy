# Известные риски

## Safety-first

Первый приоритет стратегии — сохранить капитал, маржу и позиции. Поэтому sizing/restructuring всегда должен проходить safety validation до исполнения.

## Stop Loss

**Статус: OPEN**

Stop Loss пока не подтверждён как обязательный элемент базовой стратегии.

## Рост объёма по сетке

Риск определяется не только coin qty, а распределением margin/notional по уровням.

Особенно опасны:
- слишком высокий `K` в `POWER_CURVE`;
- слишком большие `M_i` в `PER_ORDER_M`;
- высокая leverage;
- небольшой reserve;
- повторный reinvest без контроля total exposure.

Поэтому sizing mode сам по себе не является risk rule. Risk Manager должен отдельно ограничивать итоговую экспозицию.

## Minimum-lot / minimum-notional risk

При небольшом future budget часть рассчитанных orders может оказаться ниже биржевого минимума.

Нельзя допускать partial apply, когда часть новой сетки выставилась, а часть была rejected.

```text
any mandatory order invalid
→ whole plan MANUAL_REVIEW
```

## Partial fill risk

Partially-filled Entry создаёт factual position, которую нельзя считать pending intent. При restructuring filled часть immutable, future remainder может изменяться.

## Reinvestment risk

После прибыльного TP доступный капитал может увеличиться, но нельзя считать realized PnL автоматически равным свободной марже для нового sizing.

Нужен fresh factual account snapshot и подтверждённая `capital_base` semantics.

## Cross-side routing risk

Неправильный автоматический перенос капитала Long↔Short может ухудшить hedge или увеличить liquidation risk. Пока routing formula не подтверждена, она остаётся research layer.

## Общий Long / Short break-even

Нет подтверждённой единой формулы общей зоны безубытка по всем StrategyLots и двум сторонам. Это нельзя использовать как hard risk metric до формализации.

## External intervention

Ручное изменение состояния через Bybit требует reconciliation и подтверждения Adopt/Restore. Скрытая автоматическая перестройка запрещена.

## Technical races

Execution Engine обязан учитывать:
- REST timeout при фактически созданном order;
- duplicate WS/REST events;
- out-of-order executions;
- cancel vs fill race;
- reconnect;
- restart recovery;
- stale instrument metadata.

Execution является ground truth, а command acknowledgement не заменяет reconciliation.
