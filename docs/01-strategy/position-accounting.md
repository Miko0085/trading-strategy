# Учёт позиции и Strategy Lot

## Главный принцип

Нужно жёстко разделять:

```text
planned future volume
и
factual executed/open volume
```

## configured_qty

Текущий целевой суммарный объём конкретного Grid Order:

```text
configured_qty = filled_qty + remaining_entry_qty
```

В основном Manual Grid он рассчитывается sizing layer, а не обязательно вводится трейдером вручную.

## filled_qty

Сколько монет Bybit фактически исполнил по связанным ExchangeOrders этого Grid Order.

`filled_qty` является factual/immutable для sizing/restructuring.

## remaining_entry_qty

Неисполненная future часть Entry. Может изменяться при restructuring.

## open_qty

Factual объём StrategyLot, который ещё остаётся открытым после частичных TP/manual closes.

## closed_qty

Factual объём StrategyLot, который уже закрыт.

## StrategyLot появляется после первого fill

Один Grid Order может исполняться несколькими executions.

После первого execution создаётся/обновляется один StrategyLot, который хранит:
- executions;
- `filled_qty`;
- quantity-weighted factual average fill;
- `open_qty`;
- `closed_qty`;
- realized PnL;
- TP1..TP4 state.

Новые fills того же logical Grid Order не создают новые Grid Orders.

## Bybit aggregate position и внутренняя attribution

Bybit показывает агрегированную Long/Short position.

Платформа дополнительно должна помнить attribution по каждому Grid Order/StrategyLot, чтобы знать:
- какой factual volume относится к какому уровню;
- его собственную average fill;
- какие TP уже закрыли часть объёма;
- какой realized PnL связан с этим lot;
- какой future Entry remainder ещё существует.

## Sizing accounting

При перерасчёте future budget нельзя считать planned qty фактически занятым капиталом.

Нужно отдельно учитывать:
- factual used capital;
- locked future capital;
- resizable future capital.

Точная production-формула `capital_base`/used margin остаётся отдельным подтверждаемым правилом.
