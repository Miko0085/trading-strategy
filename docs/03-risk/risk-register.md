# Реестр рисков

**Статус: ИССЛЕДОВАНИЕ / БУДУЩИЙ RISK MANAGER**

## Основные классы

1. Рост суммарного exposure по Martingale/deep sizing.
2. Исчерпание available margin.
3. Нарушение Reserve policy.
4. Ликвидация при экстремальном движении.
5. Одновременное давление нескольких symbols на общий UTA capital.
6. Partial fill крупного Entry.
7. TP qty больше factual open_qty.
8. Недопустимый qtyStep/minOrderQty/minNotionalValue.
9. Неликвидность и большой spread.
10. Price gap / резкий squeeze.
11. Long/Short imbalance.
12. Отсутствие ожидаемого отскока.
13. Зависание капитала в глубоких lots.
14. Funding и комиссии.
15. Иллюзия прибыли по отдельным TP при ухудшении общей equity.
16. Ошибка dynamic sizing formula.
17. Ошибка trailing trigger.
18. Cancel/replace churn.
19. Stale account state.
20. Несовпадение factual Position Mode и planned sides.
21. API/WebSocket failure.
22. Duplicate execution event.
23. Restart recovery failure.
24. Ошибка attribution fill → StrategyLot.
25. Переобучение логики на короткой истории.

## Главный принцип будущего Risk Manager

Risk должен оцениваться на двух уровнях: Grid/Symbol level и Account level. Он не прогнозирует цену, а проверяет допустимость proposed plan при текущем капитале и factual state.
