# Эмпирические примеры торговли 13–20 сентября 2026

**Статус: OBSERVED FACT / RESEARCH**

Источник: экспорт Bybit UTA Perpetual Trade History за период 12/13–20 сентября 2026. В публичной документации не приводятся order IDs, transaction IDs и приватные account fields.

## Ограничение интерпретации

CSV содержит direction конкретного execution, но без полной связки positionIdx + StrategyLot attribution нельзя безошибочно утверждать, какой предыдущий fill был закрыт конкретным встречным execution. Поэтому ниже фиксируются фактические последовательности и осторожные выводы, а не выдуманная attribution.

## Почему LSKUSDT

Из исследованного файла LSKUSDT имеет наиболее полную историю: 37 trade/liquidation executions, тогда как по другим symbols выборка намного меньше.

## Глубокое масштабирование inventory

Фактические Long-direction executions включали:

- 20.0 @ 1.000
- 24.8 @ 0.805
- 81.9 @ 0.610
- 136.0 @ 0.441
- 175.9 @ 0.341

Наблюдение: размер executions существенно увеличивался на более глубоких ценах. Паттерн согласуется с deep-level sizing/Martingale, но точный коэффициент по этой выборке не выводится.

## Partial unload pattern

Фактические последовательности включают:

- Long-direction 36.3 @ 0.550; позже Short-direction 20.0 @ 0.610;
- Long-direction 55.3 @ 0.452; позже Short-direction 30.0 @ 0.505;
- Long-direction 69.6 @ 0.431; позже Short-direction 20.0 @ 0.481 и 20.0 @ 0.500.

Если рассматривать эти пары как гипотезу lot-level unload, движения составляют примерно +10.9%, +11.7%, +11.6%/+16%, а объём первой/совокупной разгрузки близок к половине исходного quantity.

Статус: СИЛЬНО ПОДДЕРЖИВАЕМАЯ ГИПОТЕЗА, не universal rule.

## Forced close / tail risk

13 сентября в LSKUSDT присутствует liquidation execution 283.8 @ 1.48039 после серии Short-direction limit executions на растущих ценах. Это подтверждает класс риска: последовательное наращивание exposure против сильного движения может закончиться forced close.

## Архитектурные выводы

- нужен StrategyLot/Filled Allocation;
- aggregate position недостаточна;
- нужен account-level Risk Manager;
- deep sizing должен проходить capital allocation guard;
- partial fill и factual qty должны быть first-class;
- короткая выборка не даёт права зашивать точные TP/Martingale/recovery constants.
