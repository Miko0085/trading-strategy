# Execution Engine — механизм безопасного исполнения

**Статус: СЛЕДУЮЩИЙ СЛОЙ ПЛАТФОРМЫ / ЕЩЁ НЕ РЕАЛИЗОВАН**

Execution Engine — отдельный write-capable компонент. Его задача — не принимать стратегические решения, а безопасно исполнять уже утверждённый план.

## Вход

Execution Engine получает ApprovedExecutionPlan с конкретными PLACE / AMEND / CANCEL / TP actions, qty, price, side и source revision.

## Обязанности

- валидировать команду;
- проверять Bybit instrument limits;
- обеспечивать idempotency;
- защищаться от duplicate command;
- отправлять write-запрос;
- отслеживать ack/order state;
- связывать ExchangeOrder с исходной конфигурацией;
- отслеживать fills;
- синхронизировать TP;
- выполнять reconciliation;
- сохранять command audit;
- безопасно восстанавливаться после restart.

## Что Execution Engine не решает

Он не должен:
- выбирать новый qty;
- рассчитывать compound allocation;
- решать, когда сделать restructuring;
- выбирать новую Grid Revision;
- изменять Long / Short allocation;
- определять, хватает ли risk budget;
- прогнозировать рынок.

Это обязанности Decision Layer и Risk Manager.

## Active Order Window

Execution Engine механически применяет политику Active Order Window, заданную текущей Grid Revision.

Он не решает сам, сколько уровней должно быть активно.

## Частичные fills и TP

После первого fill:
- появляется фактически исполненный объём;
- обновляется filled_qty;
- пересчитывается actual average entry;
- TP рассчитывается от фактического объёма;
- TP выставляется лимитными заявками.

Технический способ синхронизации TP при последующих fills ещё требует отдельного решения.

## Ручные изменения через интерфейс

Изменение трейдером параметров платформы должно сначала формировать новую revision/plan, после чего Execution Engine применяет разрешённые изменения.

Execution Engine не должен редактировать стратегическую конфигурацию сам.

## Внешнее вмешательство через терминал Bybit

При обнаружении расхождения:
- остановить автоматическое предположение о текущем state;
- уведомить трейдера;
- получить подтверждение;
- принять external state либо восстановить platform state, если это не требует самостоятельного нового trade decision.

Уже случившиеся executions не откатываются.

## Биржевые ограничения

Перед каждым PLACE/AMEND получать или использовать актуальный cache Bybit instrument metadata и проверять:
- minOrderQty;
- qtyStep;
- minNotionalValue;
- tickSize.

Нельзя глобально хардкодить минимальный order size.

## Safety requirements

Обязательны:
- separate write-enabled API key;
- paper/testnet-first;
- command idempotency;
- audit trail;
- reconciliation;
- restart recovery;
- kill switch;
- explicit command validation;
- запрет импортировать write path в Recorder.