# Обзор стратегии

**Статус: TRADER EXPLANATION / CANDIDATE**

## Общая картина

Трейдер торгует вручную по системе, использующей:

- Hedge Mode на Bybit — Long и Short одновременно по одному символу (`OBSERVED FACT`, подтверждено на реальных данных UAIUSDT — см. [05-research/trader-observations.md](../05-research/trader-observations.md));
- сетки лимитных ордеров (Grid Orders) на обеих сторонах;
- рост объёма ордера глубже по сетке (`CANDIDATE`, качественно наблюдается, формулы нет — см. [grid-mechanics.md](grid-mechanics.md));
- независимый учёт каждого исполненного уровня как Strategy Lot;
- частичные фиксации (partial TP) относительно цены входа конкретного lot, а не общей средней позиции;
- ручную перестройку/добавление ордеров по решению трейдера.

## Компоненты

| Документ | Что описывает |
|---|---|
| [long-short-model.md](long-short-model.md) | Как устроены Long/Short как две независимые сетки |
| [grid-mechanics.md](grid-mechanics.md) | Как выставляются уровни сетки и их объём |
| [order-model.md](order-model.md) | Правила именования/учёта ордера как объекта |
| [partial-take-profit.md](partial-take-profit.md) | Как считается частичный TP и от чего |
| [position-accounting.md](position-accounting.md) | Coin quantity, Strategy Lot vs Bybit-агрегация |
| [examples.md](examples.md) | Реальные примеры по UAIUSDT с ID ордеров |

## Что подтверждено, а что нет

Ничего из перечисленного выше не имеет статуса `CONFIRMED` как точная формула, кроме одного явно подтверждённого правила про TP (см. [partial-take-profit.md](partial-take-profit.md)). Полный список подтверждённых и неподтверждённых пунктов — в [05-research/confirmed-rules.md](../05-research/confirmed-rules.md) и [05-research/candidate-rules.md](../05-research/candidate-rules.md).
