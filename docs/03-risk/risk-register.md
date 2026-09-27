# Реестр рисков

**Статус: ИССЛЕДОВАНИЕ / БУДУЩИЙ RISK MANAGER**

Этот список не является набором торговых правил. Он фиксирует классы рисков, которые должны быть учтены при формализации Risk Manager и Execution Safety.

## Риски стратегии и позиции

1. Перекос между Long и Short.
2. Слишком большая суммарная позиция.
3. Накопление большого объёма по сетке.
4. Слишком крутой Power Curve (`K`).
5. Слишком большой `M_i` отдельного Grid Order.
6. Высокая leverage при глубокой сетке.
7. Исчерпание available margin.
8. Недостаточный reserve.
9. Ликвидация.
10. Большая просадка без ликвидации.
11. Ошибочное использование realized/unrealized PnL как свободного budget.
12. Двойной учёт margin/equity/PnL при sizing.
13. Ошибочный cross-side reinvestment.
14. Несимметричное исполнение Long/Short.
15. Цена долго не достигает TP.
16. Плохая weighted average стороны.
17. Ловушка усреднения.
18. Актив долго не восстанавливается.
19. Резкий рост цены против Short.
20. Funding.
21. Комиссии.
22. Долгая блокировка капитала.
23. Экстремальное движение / tail risk.
24. Концентрация капитала в одном активе.
25. Делистинг / остановка торгов.
26. Недоступность биржи / counterparty risk.

## Sizing / restructuring risks

27. Future budget меньше суммы минимально исполнимых orders.
28. Один level после ROUND_DOWN падает ниже `minOrderQty`.
29. Notional падает ниже `minNotionalValue`.
30. Ошибка `qtyStep`/`tickSize` normalization.
31. Partial apply нового плана: часть orders выставилась, часть rejected.
32. Restructuring затронул factual filled volume.
33. Manual lock случайно перезаписан full-grid recalculation.
34. Profit-taking trigger сработал на stale account state.
35. Повторный trigger применил reinvestment дважды.
36. Новый GridOrder изменил weights существующих orders неожиданным образом.
37. В `PER_ORDER_M` изменение одного `M_i` каскадно изменило последующие weights без preview.
38. В `POWER_CURVE` изменение `N` после добавления level изменило весь профиль weights без явного пересчёта/revision.

## Execution/API risks

39. Ошибка API/WebSocket.
40. REST timeout при фактически созданном order.
41. Дублирование WS/REST execution.
42. Out-of-order events.
43. Cancel vs Fill race.
44. Amend vs partial fill race.
45. Stale instrument metadata.
46. Reconnect без reconciliation.
47. Restart между command и factual confirmation.
48. Duplicate order после retry.
49. Неправильный `positionIdx` в Hedge Mode.
50. Неверный environment/API key permissions.
51. Rate limit / throttling.
52. Partial batch success.
53. External manual intervention на Bybit.

## Исследовательские риски

54. Ошибка формализации стратегии.
55. Скрытое правило трейдера не попало в алгоритм.
56. Реальные ручные решения отличаются от формальной модели.
57. Переобучение на короткой истории.
58. Нереалистичный simulation/backtest.
59. Смешивание candidate rule с confirmed rule.
60. Отсутствие независимого emergency/risk layer.

## Главные темы следующего исследования

- production `capital_base`;
- liquidation/risk metrics;
- reinvestment routing Long/Short;
- same-side vs cross-side vs both-side reinvest;
- минимальный рабочий capital для полной Grid;
- допустимая крутизна sizing;
- reserve;
- automatic rebase/trailing;
- emergency actions.

Точные пороги и autonomous actions не должны появляться без отдельного подтверждения и тестирования.
