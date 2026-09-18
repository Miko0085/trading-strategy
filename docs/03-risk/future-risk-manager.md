# Future Risk Manager

**Статус: FUTURE** — не реализуется на текущем этапе.

## Что это

Risk Manager — отдельная будущая надстройка (Phase 3, см. [06-development/roadmap.md](../06-development/roadmap.md)). Сейчас **не реализуется**:

- dynamic TP adaptation;
- forced unloading;
- automatic exposure reduction;
- emergency close;
- auto rebalancing;
- automatic capital allocation.

## Что он потенциально будет отслеживать (без формул и порогов на этом этапе)

- equity;
- available balance;
- available margin;
- Long exposure;
- Short exposure;
- margin utilization;
- risk limits;
- capital allocation.

Точные formulas/thresholds сейчас **неизвестны** и не придумываются заранее.

## Risk Manager не предсказывает рынок

Будущий Risk Manager не отвечает на вопрос «куда пойдёт рынок?». Он отвечает на вопрос:

> «Что происходит с капиталом, margin и exposure при текущем движении цены?»

Он **не использует** news, sentiment, технические индикаторы или AI price prediction — то же правило, что и для базовой стратегии (см. [00-overview/principles.md](../00-overview/principles.md)).
