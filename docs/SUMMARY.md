# Содержание

* [Документация стратегии](README.md)

## Обзор проекта

* [Обзор проекта](00-overview/project-overview.md)
* [Цели](00-overview/goals.md)
* [Принципы](00-overview/principles.md)
* [Глоссарий](00-overview/glossary.md)

## Стратегия

* [Обзор стратегии](01-strategy/strategy-overview.md)
* [Модель Long / Short](01-strategy/long-short-model.md)
* [Механика сетки](01-strategy/grid-mechanics.md)
* [Модель ордера](01-strategy/order-model.md)
* [Частичный Take Profit](01-strategy/partial-take-profit.md)
* [Учёт позиции и Strategy Lot](01-strategy/position-accounting.md)
* [Примеры механики](01-strategy/examples.md)

## Алгоритм

* [Базовый алгоритм исполнения сетки](02-algorithm/current-algorithm.md)
* [Активное окно ордеров](02-algorithm/active-order-window.md)
* [Алгоритм реструктуризации сетки](02-algorithm/restructuring-algorithm.md)
* [Жизненные циклы ордеров](02-algorithm/order-lifecycle.md)
* [Жизненный цикл Grid](02-algorithm/grid-lifecycle.md)
* [Автоматы состояний и оркестратор](02-algorithm/state-machine.md)

## Риски

* [Реестр рисков](03-risk/risk-register.md)
* [Известные риски](03-risk/known-risks.md)
* [Будущий Risk Manager](03-risk/future-risk-manager.md)

## Платформа

* [Архитектура платформы](04-platform/platform-overview.md)
* [Роль Recorder](04-platform/recorder-role.md)
* [Интеграция с Bybit](04-platform/bybit-integration.md)
* [Модель данных](04-platform/data-model.md)
* [Execution Engine](04-platform/future-execution-engine.md)

## Исследование стратегии

* [Наблюдения трейдера](05-research/trader-observations.md)
* [Наблюдения по реструктуризации](05-research/restructuring-observations.md)
* [Маршрутизация реинвеста и автоматическая реструктуризация](05-research/reinvestment-routing-research.md)
* [Гипотезы и возможные правила](05-research/candidate-rules.md)
* [Подтверждённые правила](05-research/confirmed-rules.md)
* [Открытые вопросы](05-research/open-questions.md)
* [Противоречия](05-research/contradictions.md)

## Разработка

* [План разработки](06-development/roadmap.md)
* [История изменений](06-development/changelog.md)
* [Журнал решений](06-development/decisions.md)