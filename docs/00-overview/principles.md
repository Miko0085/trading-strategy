# Принципы

**Статус: ПОДТВЕРЖДЕНО ДЛЯ ВСЕГО ПРОЕКТА**

## 1. Безопасность капитала — первый приоритет

Порядок приоритетов стратегии:

```text
1. сохранить капитал и маржу
2. не допустить неконтролируемого liquidation risk
3. улучшать средние цены и структуру hedge
4. только после этого оптимизировать прибыль
```

Risk/safety проверки не должны подменяться торговыми прогнозами.

## 2. Стратегия является математической системой

Цена и состояние счёта используются как объективные входные данные.

Внешняя информация о причинах движения цены не используется.

## 3. Long, Short и отдельные Grid Orders автономны

Long и Short конфигурируются независимо. Каждый Grid Order является отдельной сущностью и может иметь собственные Entry, sizing parameters, TP и factual history.

Одинаковые уровни, объёмы и Martingale для двух сторон не предполагаются автоматически.

## 4. Geometry и Sizing разделены

```text
Grid Geometry = где расположен Entry
Grid Sizing   = сколько капитала/номинала получает Entry
```

Пересчёт объёма сам по себе не должен менять вручную заданную цену уровня.

## 5. Sizing считается через капитал и номинал

Канонический pipeline:

```text
Future Margin Budget
→ leverage
→ Future Notional Budget
→ sizing weights
→ notional per Grid Order
→ qty = notional / entry_price
→ Bybit normalization/validation
```

Martingale/weight distribution применяется к денежному размеру позиции, а не напрямую к coin qty.

## 6. Factual reality immutable

Execution/Fill является фактом. Уже исполненный объём не пересчитывается задним числом.

```text
filled/open qty = factual
pending/future qty = intent
```

## 7. Биржевые ограничения — hard execution invariant

Ни один Entry, TP, recovery или restructured order не может перейти к исполнению, если нарушает актуальные Bybit instrument limits.

Если обязательный ордер плана не проходит `minOrderQty`, `qtyStep`, `minNotionalValue` или `tickSize`, весь соответствующий Execution/Restructuring Plan блокируется и уходит в `MANUAL_REVIEW`; partial apply запрещён.

## Что запрещено использовать как торговый сигнал

- RSI, MACD, Moving Average, Bollinger Bands, Stochastic и другие технические индикаторы;
- Fear & Greed;
- новости;
- social sentiment;
- прогнозы аналитиков;
- AI price prediction;
- фундаментальные или макроэкономические оценки;
- мнение других трейдеров;
- субъективное «ощущение рынка».

## Какие данные использовать можно

- Market / Mark / Index Price;
- Entry/TP price;
- фактическая цена исполнения;
- qty / notional;
- Long / Short position;
- average entry;
- realized / unrealized PnL;
- wallet balance / equity / available margin;
- leverage;
- fees / funding;
- active orders / executions;
- Bybit instrument metadata;
- position mode и factual account state.

## Правила ведения знаний

1. Не превращать пример в универсальное правило.
2. Не повышать гипотезу до CONFIRMED без явного подтверждения.
3. Отделять intent от factual Bybit state.
4. Отделять Recorder от Execution Engine.
5. Сохранять Grid Revision и before/after audit.
6. Не скрывать противоречия и неизвестные места.
7. Risk Manager не прогнозирует рынок.
8. Если новое прямое подтверждение трейдера заменяет старое правило, старое помечается `SUPERSEDED`.
