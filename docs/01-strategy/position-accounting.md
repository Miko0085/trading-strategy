# Учёт позиции и Strategy Lot

## Основные количества

- configured_qty — целевой объём Entry;
- filled_qty — реально исполненный объём;
- open_qty — factual filled qty минус уже закрытый объём;
- closed_qty — уже разгруженный factual qty.

## Aggregate Position ≠ Strategy Lot

Bybit объединяет Long/Short в агрегированную позицию. Платформа должна отдельно знать происхождение каждого объёма: source GridOrderConfig, executions, actual average fill, open_qty, closed_qty, realized PnL и TP configuration.

Это позволяет конкретному глубокому lot быть прибыльно разгруженным независимо от aggregate average всей стороны.

## Частичные fills

Несколько fills одного Entry не создают несколько Grid Orders. После первого fill StrategyLot уже существует в состоянии accumulating и обновляет filled_qty/avg fill по мере новых executions.

## PnL decomposition

Для аналитики отдельно учитываются realized PnL по Strategy Lots, unrealized PnL, fees, funding и liquidation/forced-close effects.

Нельзя оценивать стратегию только по отдельным успешным partial closes или только по текущей aggregate average.
