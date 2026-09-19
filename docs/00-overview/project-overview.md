# Обзор проекта

**Статус: ПОДТВЕРЖДЁННАЯ АРХИТЕКТУРА / ИССЛЕДУЕМАЯ СТРАТЕГИЯ**

Проект разделён на независимые слои.

## 1. Recorder — что реально произошло

Read-only контур, который записывает рынок, orders, executions, positions, wallet, trader notes и timeline.

Recorder никогда не торгует.

## 2. Strategy / Configuration — что трейдер хочет сделать

Здесь хранятся подтверждённые правила, Grid Revision и параметры, введённые трейдером.

## 3. Decision Layer — что нужно сделать сейчас

Состоит из двух направлений:
- Base Grid Planner — механически строит текущую сетку;
- Restructuring Planner — в будущем формирует RestructuringPlan.

Decision Layer не имеет прямого доступа к Bybit.

## 4. Risk Manager — можно ли это делать

Получает proposed plan и возвращает ALLOW / MODIFY / DENY.

## 5. Execution Engine — как безопасно исполнить

Получает утверждённый Execution Plan и детерминированно выполняет его через Bybit API.

Он не выбирает sizing, не решает когда реструктурировать Grid и не принимает risk decisions.

## 6. Research

Связывает:
- trader intent;
- configuration;
- фактические Bybit events;
- trader explanation;
- result.

Цель — формализовать оставшиеся неизвестные правила, прежде всего реструктуризацию.

## Главная архитектурная формула

```text
DECISION = что хотим сделать
RISK     = можно ли это делать
EXECUTION= как это безопасно сделать
RECORDER = что реально произошло
```