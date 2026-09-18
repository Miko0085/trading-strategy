# Configurable Grid Execution Engine

**Статус: NEXT PLATFORM LAYER / NOT YET IMPLEMENTED**

Этот компонент отделён от read-only Strategy Recorder.

## Назначение

Execution Engine должен механически исполнять **заранее заданную трейдером конфигурацию**, не пытаясь самостоятельно предсказывать рынок или выбирать стратегические параметры.

Он сможет:

- хранить конфигурацию Long Grid и Short Grid;
- хранить N Grid Orders на сторону;
- задавать coin quantity каждого Grid Order;
- рассчитывать следующий limit price от предыдущего configured limit price;
- размещать/отменять сконфигурированные limit orders;
- собирать executions конкретного source order в Strategy Lot;
- считать actual average execution price lot;
- хранить original_qty / closed_qty / remaining_qty;
- поддерживать 0..N partial TP steps;
- считать TP от entry конкретного Strategy Lot;
- считать каждый close percentage от original_qty;
- принимать ручное изменение параметров;
- вести audit trail изменений.

## Важное изменение roadmap

Для разработки этой **механической** части не требуется ждать полной формализации decision logic стратегии.

Параллельно:

- Recorder продолжает собирать факты и объяснения;
- Research слой формализует правила;
- Execution Engine может исполнять явно заданную конфигурацию.

## Что сюда пока НЕ входит

- автоматический выбор spacing;
- автоматический sizing;
- прогноз направления рынка;
- новости/sentiment/technical indicators;
- автоматическое приближение TP по риску;
- автоматическое перераспределение Long/Short;
- Risk Manager;
- автономная торговая decision logic.

До отдельного решения Recorder остаётся strictly read-only. Write-enabled Bybit доступ должен принадлежать отдельному Execution Engine с собственными safety controls.
