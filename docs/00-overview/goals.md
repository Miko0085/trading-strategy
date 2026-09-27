# Цели проекта

## Главная цель

Построить детерминированную торговую платформу для Hedge Mode, которая воспроизводит подтверждённую механику трейдера, автоматизирует расчёт объёмов и безопасно исполняет Long/Short Grid без внешних торговых сигналов.

Главный приоритет стратегии — **сохранение капитала, маржи и позиций**. Оптимизация прибыли идёт после проверки безопасности и допустимости позиции.

## 1. Зафиксировать реальную стратегию

Нужно постоянно связывать:
- что трейдер хотел сделать;
- какую Grid Revision настроил;
- что реально произошло на Bybit;
- почему он изменил параметры;
- как изменились average price, margin, exposure и PnL.

Recorder остаётся источником factual history и никогда не торгует.

## 2. Формализовать Manual Grid

Платформа должна поддерживать:
- независимые Long Grid и Short Grid;
- автономный GridOrderConfig для каждого уровня;
- ручную геометрию Entry Price / Percent;
- автоматический sizing из разрешённого future budget;
- два необходимых режима распределения объёма: `POWER_CURVE` и `PER_ORDER_M`;
- Active Order Window;
- partial fills и StrategyLot после первого fill;
- максимум четыре TP parts на один StrategyLot;
- Grid Revision и полный before/after audit.

## 3. Автоматизировать перерасчёт future volume

При изменении капитала или исполнении прибыльного TP система должна уметь пересчитать future часть сетки, не изменяя factual fills.

Подтверждённое направление:

```text
Factual filled/open volume = immutable
Future/pending volume      = recalculable
```

Profit-taking event является trigger для нового расчёта/restructuring proposal. Точная маршрутизация нового капитала между Long и Short остаётся отдельным исследовательским вопросом.

## 4. Сделать execution технически безопасным

Перед запуском и перед каждым новым Execution Plan обязательны:
- актуальные Bybit instrument limits;
- `minOrderQty`;
- `qtyStep`;
- `minNotionalValue`;
- `tickSize`;
- проверка position mode;
- проверка budget/risk constraints.

Если хотя бы один обязательный ордер плана технически невалиден, план не применяется частично и уходит в `MANUAL_REVIEW`.

## Дальнейшие этапы

- simulation / shadow / testnet;
- формализация reinvestment routing;
- Risk Manager;
- controlled write execution;
- автоматическая реструктуризация только после подтверждения всех decision rules.

## Что не является целью

- прогнозировать направление рынка;
- использовать RSI/MACD/новости/sentiment/AI price prediction;
- автоматически придумывать неизвестные правила;
- считать Long и Short симметричными по sizing или risk;
- смешивать Recorder и Execution Engine.
