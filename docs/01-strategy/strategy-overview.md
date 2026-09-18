# Обзор стратегии

**Статус: MIXED — CONFIRMED mechanics + CANDIDATE decision logic**

## Что уже подтверждено

Базовая механика стратегии сейчас описывается так:

- стратегия работает с Long и Short в Hedge Mode;
- Long и Short ведутся как две отдельные сетки по одному инструменту;
- Grid Orders — лимитные ордера;
- параметры каждого Grid Order задаются индивидуально и могут отличаться;
- основной размер ордера задаётся в количестве монет (coin quantity), а не в долларах маржи;
- цена следующего Grid Order может рассчитываться от limit price предыдущего Grid Order;
- после фактического исполнения Grid Order его исполненный объём должен учитываться как отдельный Strategy Lot;
- partial Take Profit конкретного Strategy Lot считается от actual average execution price именно этого lot;
- каждый partial close считается от original_qty именно этого lot;
- конкретные проценты spacing, sizing и TP не являются универсальными константами;
- внешние сигналы, новости, sentiment и технические индикаторы не используются.

## Что ещё НЕ формализовано

Пока нет подтверждённой универсальной формулы для:

- количества монет следующего Grid Order;
- изменения spacing по глубине сетки;
- количества Grid Orders;
- автоматической перестройки сетки;
- автоматического приближения TP;
- Stop Loss;
- распределения капитала Long/Short;
- combined break-even;
- Risk Manager thresholds.

## Важное архитектурное уточнение

Для реализации базовой механики **не требуется ждать полной формализации всей стратегии**.

Можно параллельно развивать два слоя:

1. **Strategy Recorder / Research** — наблюдает реальную торговлю и помогает формализовать decision logic.
2. **Manual-configured Grid Execution Engine** — механически исполняет заранее заданные трейдером параметры Grid Orders и partial TP, не решая самостоятельно, почему выбраны именно эти параметры.

Автоматическое принятие стратегических решений и Risk Manager остаются более поздними фазами.

## Связанные документы

- [Long / Short](long-short-model.md)
- [Grid Mechanics](grid-mechanics.md)
- [Order Model](order-model.md)
- [Partial Take Profit](partial-take-profit.md)
- [Position Accounting](position-accounting.md)
- [Confirmed Rules](../05-research/confirmed-rules.md)
- [Open Questions](../05-research/open-questions.md)
