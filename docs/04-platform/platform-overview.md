# Platform Overview

**Статус: OBSERVED FACT (Recorder) / NEXT PLATFORM LAYER (Execution Engine) / FUTURE (Risk Manager)**

Платформа разделена на независимые слои:

```text
┌────────────────────────────────────────────┐
│ Strategy / Platform Documentation          │
│ docs/                                      │
├────────────────────────────────────────────┤
│ Configurable Grid Execution Engine         │
│ NEXT PLATFORM LAYER                        │
│ mechanical execution of trader config      │
├────────────────────────────────────────────┤
│ Future Risk Manager                        │
│ FUTURE independent layer                   │
├────────────────────────────────────────────┤
│ Bybit Strategy Recorder                    │
│ EXISTS / PERMANENTLY READ-ONLY             │
│ src/recorder/                               │
├────────────────────────────────────────────┤
│ Bybit V5                                   │
└────────────────────────────────────────────┘
```

## 1. Strategy Recorder

Recorder уже существует и остаётся **permanently read-only**.

Он отвечает за:

- raw Bybit events;
- orders / executions / positions / wallet;
- market context;
- reconciliation;
- trader notes / voice;
- timeline;
- dataset export;
- machine truth.

Recorder никогда не должен размещать, изменять или отменять реальные ордера.

## 2. Configurable Grid Execution Engine

Execution Engine — **отдельный компонент**, который разрешено разрабатывать параллельно с исследованием стратегии.

Его задача — механически исполнять уже заданную трейдером конфигурацию:

- Long Grid / Short Grid;
- N configurable Grid Orders;
- coin quantity per order;
- Strategy Lot accounting;
- partial TP steps;
- manual amend/cancel;
- audit trail.

Он не обязан ждать полной формализации причины выбора spacing/qty/TP.

Но он не должен сам придумывать эти параметры.

Подробнее: [future-execution-engine.md](future-execution-engine.md).

## 3. Risk Manager

Risk Manager — отдельный будущий слой.

Он будет контролировать:

- margin;
- equity;
- exposure;
- allocation limits;
- risk states;
- emergency actions.

Он не прогнозирует рынок и не использует новости, sentiment или technical indicators.

## 4. Жёсткая граница компонентов

```text
Recorder
  READ ONLY
  ↓
observes reality

Execution Engine
  WRITE CAPABLE
  ↓
executes explicit configuration

Risk Manager
  FUTURE
  ↓
may allow/deny/modify actions by confirmed risk rules
```

API keys, runtime responsibilities и safety boundaries у Recorder и Execution Engine должны быть раздельными.

## 5. Documentation layer

`docs/` хранит canonical knowledge:

- confirmed mechanics;
- candidate rules;
- open questions;
- architecture decisions;
- roadmap.

Документация не является runtime-компонентом и не должна содержать приватные account dumps/API secrets.


## 6. External intervention reconciliation

Если фактическое состояние Bybit отличается от состояния, ожидаемого по последней конфигурации платформы, это считается external intervention / state divergence.

Execution Engine не адаптирует стратегию самостоятельно.

Допустимы только два подтверждённых трейдером действия:

1. Adopt external state — принять ручное изменение как новое фактическое состояние и вручную обновить конфигурацию платформы.
2. Restore platform state — восстановить последнюю подтверждённую конфигурацию платформы из revision history там, где это технически возможно без создания нового самостоятельного торгового решения.

Любое уже совершившееся execution/manual close остаётся machine truth и не «откатывается». Recorder при этом продолжает независимо фиксировать фактические события Bybit.
