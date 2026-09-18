# Risk Register

**Статус: RESEARCH / FUTURE RISK MANAGER**

Этот список не является торговыми правилами. Он фиксирует классы риска, которые позже должны быть проверены и формализованы.

## Position / strategy risks

1. Long/Short directional imbalance.
2. Слишком большой gross exposure.
3. Накопление grid exposure.
4. Martingale / increasing sizing tail risk.
5. Exhaustion of available margin.
6. Liquidation.
7. Большой equity drawdown без liquidation.
8. Использование unrealized PnL как расчётного budget.
9. Reversal после добавления противоположной стороны.
10. Отсутствие требуемого rebound.
11. Актив не восстанавливается / длительная стагнация.
12. Extreme pump против Short.
13. Path dependency.
14. Whipsaw.
15. Неудачная aggregate average price.
16. Average-price trap.
17. TP не достигается.
18. Partial fill.
19. Асимметрия исполнения Long/Short.
20. Slippage.
21. Недостаточная liquidity.
22. Spread.
23. Market impact.
24. Funding.
25. Fees.
26. Realized-profit illusion при плохом total equity.
27. Долгая блокировка капитала / Time Under Water.
28. Изменение volatility regime.
29. Concentration risk.
30. Correlation risk между активами.
31. Parameter risk.
32. Недостаточный risk budget.
33. Scaling risk при увеличении капитала.
34. Tail / black-swan move.
35. Delisting / failure конкретного token.
36. Exchange outage.
37. Counterparty / exchange risk.

## Technical / execution risks

38. API/WebSocket failure.
39. Stale state.
40. Duplicate event.
41. Order rejection.
42. Latency.
43. Software bug.
44. Restart / state recovery failure.
45. Ошибка формализации стратегии.
46. Скрытое правило трейдера не попало в алгоритм.
47. Human discretion отличается от формальной модели.
48. Overfitting.
49. Нереалистичный backtest/simulation.
50. Отсутствие независимого emergency risk layer.

## Приоритет следующего исследования

До автоматизации Risk Manager особенно важно понять:

- Short uPnL -> Long allocation и поведение при reversal;
- capital exhaustion / solvency buffer;
- зависимость от rebound;
- worst price path;
- martingale/grid tail;
- dead coin / extreme pump;
- maximum acceptable equity drawdown;
- скрытые защитные правила трейдера.

Точные thresholds и автоматические действия пока не подтверждены.
