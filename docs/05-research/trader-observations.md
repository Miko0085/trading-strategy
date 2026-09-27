# Наблюдения трейдера

**Статус: OBSERVED FACTS + TRADER EXPLANATIONS**

Публичная документация содержит только обобщённые наблюдения и не публикует приватную историю счёта.

## Что уже известно

- используется Hedge Mode;
- Long и Short могут существовать одновременно;
- стороны конфигурируются независимо;
- Grid Orders являются автономными логическими уровнями;
- параметры разных уровней могут существенно отличаться;
- объём глубже по сетке может увеличиваться;
- sizing удобнее считать через margin/notional, а qty получать из Entry Price;
- отдельный order может иметь свой Martingale multiplier или не иметь увеличения (`M=1`);
- Long и Short не обязаны использовать одинаковую sizing curve;
- после первого fill уже появляется factual StrategyLot attribution;
- partial TP используется для фиксации результата и высвобождения капитала;
- на один Grid Order достаточно максимум четырёх TP parts;
- profitable TP рассматривается как trigger нового перерасчёта future budget;
- основной будущий смысл restructuring — улучшать эффективность всей стороны/позиции, а не обязательно возвращать прибыль в тот же order;
- безопасность капитала и маржи приоритетнее максимизации прибыли;
- внешние новости, индикаторы и sentiment не используются.

## Объяснение трейдера о Long / Short

**TRADER EXPLANATION:** Short внутри этой стратегии воспринимается прежде всего как hedge/защитная сторона и может иметь совсем другой sizing profile, чем Long.

Это объяснение относится к данной стратегии и не является универсальным рыночным утверждением.

## Что нужно собирать дальше

Особенно важно связывать:

```text
profit-taking event
→ factual account change
→ trader redistribution decision
→ new Grid Revision
→ resulting Long/Short averages
→ resulting margin/liquidation state
```

Нужно накопить случаи, где после прибыльного закрытия реально меняются обе стороны, чтобы восстановить cross-side routing rule.

## Что нельзя выводить из короткой истории

- финальную формулу `capital_base`;
- универсальный процент Martingale;
- универсальный `K`;
- формулу Long↔Short reinvestment;
- risk thresholds;
- recovery/trailing rule.

## Правило публикации

Реальные order IDs, event IDs, приватная account history, voice files и raw account data не публикуются в GitBook.
