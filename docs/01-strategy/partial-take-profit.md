# Частичный Take Profit

**Статус: ПОДТВЕРЖДЁННАЯ БАЗОВАЯ МЕХАНИКА**

## От какой цены считается Take Profit

Take Profit конкретного Grid Order / StrategyLot считается от его собственной factual average fill.

Не от общей average Long/Short position, не от предыдущего TP и не от исходной Mark Price.

## От какого объёма считается разгрузка

TP рассчитывается только от factual `open_qty`/`filled_qty`, а не от ещё не исполненной future части Entry.

## Максимум четыре TP parts

Для одного StrategyLot используется максимум:

```text
TP1
TP2
TP3
TP4
```

Доли не обязаны быть `25/25/25/25`. Трейдер может настроить разные части, но суммарный closing qty не может превышать factual `open_qty`.

## TP — лимитный order

Обычный TP выставляется как closing Limit order. Market не является базовым способом обычного Take Profit.

## Partial Entry

После первого fill уже существует StrategyLot и TP может рассчитываться на factual filled/open volume.

Если Entry позже получает дополнительные fills, нужно технически определить, как обновлять уже выставленные TP в рамках максимум четырёх TP parts. Это остаётся OPEN edge case.

## Profitable TP — trigger реструктуризации

Исполнение прибыльного TP/close является подтверждённым trigger для нового расчёта:

```text
TP factual fill
→ refresh account state
→ recalculate future budget
→ generate new sizing/restructuring proposal
```

Это не означает автоматически, что profit возвращается в тот же order или ту же сторону. Routing Long/Short остаётся OPEN.

## Audit

Каждый TP должен быть связан с:
- source StrategyLot;
- source GridOrderConfig;
- factual execution(s);
- closed qty;
- realized PnL / fees;
- restructuring trigger id, если он создан;
- последующей Grid Revision, если proposal применён.
