# Order Lifecycle

**Статус: OBSERVED FACT** (состояния — стандартные статусы Bybit V5, уже фиксируются Recorder'ом)

## Состояния ордера (Bybit)

```
New → PartiallyFilled → Filled
New → Cancelled
New → Rejected
New → Untriggered → Triggered → Filled/Cancelled
```

Наблюдались в реальных данных (UAIUSDT): `New`, `Filled`, `Cancelled` — см. [01-strategy/examples.md](../01-strategy/examples.md).

## Критическое правило

`order lifecycle != execution`. Статус `Filled` на ордере — это состояние ордера, а не гарантия того, что конкретное количество монет исполнилось именно так, как ожидалось. Источник истины по факту сделки — **execution** (со своим `execId`), не статус ордера. Один ордер может иметь несколько executions (частичные исполнения). Подробнее — [04-platform/bybit-integration.md](../04-platform/bybit-integration.md).

## Что не формализовано

- Условие, при котором неисполненный лимитный ордер отменяется трейдером (вопрос 4 в [05-research/open-questions.md](../05-research/open-questions.md)).
- Формальная связь между отменой ордера и перестройкой сетки.
