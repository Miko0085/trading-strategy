# Принципы

**Статус: CONFIRMED (project-wide rule)**

## Главный принцип стратегии

> Стратегия — детерминированная математическая система.

Базовая стратегия **не использует внешние сигналы** для принятия решений.

### Запрещено использовать как вход для решений стратегии

- RSI, MACD, Moving Average, Bollinger Bands, Stochastic и любые другие технические индикаторы;
- Fear & Greed и другие сторонние market indicators;
- новости и новостной фон;
- sentiment, social media;
- прогнозы аналитиков;
- AI price prediction;
- фундаментальный анализ;
- макроэкономические события;
- мнение других трейдеров;
- эмоциональную оценку рынка.

### Разрешены только объективные данные биржи, нужные для механики

- market price, mark price, index price (при необходимости);
- order price, execution price;
- coin quantity, Long qty, Short qty;
- average entry;
- realized PnL, unrealized PnL;
- equity, balance, available margin;
- leverage, fees, funding;
- active orders, executions, position state.

### Формулировка

> Цена и состояние аккаунта являются входными переменными математического алгоритма. Внешняя информация о причинах движения цены не используется.

Это правило действует и на будущий Risk Manager: он отвечает на вопрос «что происходит с капиталом, margin и exposure при текущем движении цены», а не «куда пойдёт рынок» — см. [03-risk/future-risk-manager.md](../03-risk/future-risk-manager.md).

## Производные принципы ведения знания

1. **Не додумывать.** Пример из объяснения трейдера не становится правилом автоматически. Различаем `OBSERVED FACT`, `TRADER EXPLANATION`, `CANDIDATE`, `CONFIRMED` (см. [glossary.md](glossary.md) и `05-research/`).
2. **Не повышать статус без подтверждения.** `CANDIDATE` → `CONFIRMED` только с явным подтверждением трейдера.
3. **Coin quantity — основная единица объёма**, не долларовая маржа (см. [01-strategy/position-accounting.md](../01-strategy/position-accounting.md)).
4. **Recorder — источник истины по фактам** (Bybit machine truth), объяснения трейдера — отдельный, не смешиваемый слой (см. [04-platform/recorder-role.md](../04-platform/recorder-role.md)).
5. **Сначала механика, потом правила, потом алгоритм, потом тесты, и только потом автоматизация** торговых решений (см. [06-development/roadmap.md](../06-development/roadmap.md)).
