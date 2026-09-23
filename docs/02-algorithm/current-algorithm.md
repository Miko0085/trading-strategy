# Базовый алгоритм исполнения сетки

**Статус: ПОДТВЕРЖДЁННАЯ МЕХАНИКА**

Этот алгоритм отвечает на вопрос:

> Как механически подготовить и исполнять уже заданную трейдером Manual Grid?

Он не принимает автономных торговых решений и не выбирает рынок/направление.

## Базовый поток

```text
Запуск стратегии
↓
Зафиксировать текущую Mark Price
↓
Трейдер задаёт Long / Short Manual Grid Geometry
↓
Для каждого Grid Order задать:
- Entry Price или % spacing
- per-order Martingale multiplier
- TP Steps
↓
Получить свежий factual account state
↓
Рассчитать Side Budget из allocation
↓
Вычесть factual used capital и locked future capital
↓
Рассчитать cumulative Martingale weights
↓
Распределить Available Future Budget
↓
Рассчитать configured_qty / remaining_entry_qty
↓
Проверить Bybit instrument limits
↓
Активировать заданное Active Order Window
↓
Execution Engine размещает только active Entry Orders
↓
Получать Execution / Fill
↓
После первого fill:
- создать/обновить StrategyLot
- обновить filled_qty
- пересчитать actual average entry
- синхронизировать TP на factual open qty
↓
По мере исполнения уровней
активировать следующие queued Grid Orders
↓
По ручной команде трейдера:
- RECALCULATE_ORDER
или
- RECALCULATE_GRID
↓
Создать новую Grid Revision только для future intent
```

## Что относится к этому алгоритму

- Manual Grid Geometry;
- price / percentage input;
- automatic future sizing;
- per-order Martingale chain;
- factual used capital accounting;
- Active Order Window;
- GridOrderConfig → ExchangeOrder → Execution;
- partial fill semantics;
- StrategyLot accounting;
- TP от factual volume;
- ручной перерасчёт одного ордера;
- ручной перерасчёт всей future grid;
- механическое применение текущей Grid Revision.

## RECALCULATE_ORDER

Точечный перерасчёт меняет только future qty выбранного уровня.

Остальные уровни остаются без автоматического каскадного изменения. Backend обязан проверить, что выбранный новый target помещается в доступный future budget.

## RECALCULATE_GRID

Полный перерасчёт стороны использует свежий factual state и заново распределяет весь eligible future budget по cumulative per-order Martingale weights.

Factual fills и factual open position не изменяются.

## Что сюда не относится

- automatic restructuring triggers;
- autonomous capital allocation changes;
- automatic recovery;
- automatic reinvest decisions;
- полный rebase/trailing decision;
- risk limits;
- рыночные прогнозы;
- external signals.

Реструктуризация описана отдельно: [Алгоритм реструктуризации](restructuring-algorithm.md).

Политика активного окна описана отдельно: [Активное окно ордеров](active-order-window.md).
