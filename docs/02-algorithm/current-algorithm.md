# Базовый алгоритм исполнения сетки

**Статус: ПОДТВЕРЖДЁННАЯ МЕХАНИКА / ROUTING CAPITAL OPEN**

Этот алгоритм отвечает на вопрос: как подготовить и исполнить уже заданную Manual Grid без прогнозирования рынка.

## Базовый поток

```text
1. Зафиксировать current Mark Price
2. Загрузить factual account state
3. Загрузить свежие Bybit instrument limits
4. Трейдер задаёт Long / Short Manual Geometry
5. Для каждой стороны выбрать sizing mode:
   - POWER_CURVE
   - PER_ORDER_M
6. Определить Future Margin Budget стороны
7. × leverage → Future Notional Budget
8. Рассчитать raw/normalized weights
9. Рассчитать notional_i
10. qty_i = notional_i / entry_price_i
11. ROUND_DOWN по qtyStep
12. Проверить minOrderQty / minNotionalValue / tickSize
13. Если любой обязательный order invalid → MANUAL_REVIEW
14. Создать/обновить Grid Revision
15. Активировать Active Order Window
16. Execution Engine размещает только active Entry Orders
17. Получать WS/REST factual executions
18. После первого fill создать/обновить StrategyLot
19. Синхронизировать максимум TP1..TP4 на factual open qty
20. По мере исполнения активировать следующие queued levels
21. При profitable TP/close:
    - refresh factual account state
    - сформировать новый sizing/restructuring proposal
```

## POWER_CURVE

Для eligible levels `i=1..N`:

```text
raw_weight_i = (i/N)^K
```

После нормализации future notional распределяется по всей стороне.

## PER_ORDER_M

```text
w1 = 1
w_i = w_(i-1) × M_i
```

`M_i=1` означает отсутствие увеличения на данном переходе.

## Manual restructuring

### RECALCULATE_ORDER

Пересчитывает future intent выбранного order. Остальные orders не должны автоматически изменяться.

### RECALCULATE_GRID

Заново распределяет весь eligible future budget стороны по текущему sizing mode.

Factual fills/open volume не изменяются.

## Profit-taking trigger

Profit-taking event является trigger для пересчёта, но не определяет автоматически routing нового капитала.

OPEN остаётся:
- same-side reinvest;
- cross-side risk priority;
- both-sides reinvest;
- точная формула reinvestable capital.

## Hard execution boundary

Нельзя частично применять новый sizing plan, если один обязательный order не проходит биржевые limits.

```text
VALID → дальше в Risk/Execution pipeline
INVALID → MANUAL_REVIEW
```

## Что не относится к базовому алгоритму

- прогноз направления цены;
- внешние сигналы;
- automatic allocation routing между Long/Short;
- autonomous recovery/rebase/trailing;
- ещё не подтверждённые Risk Manager thresholds.

Реструктуризация: [restructuring-algorithm.md](restructuring-algorithm.md)

Sizing: [../01-strategy/martingale-sizing.md](../01-strategy/martingale-sizing.md)

Active Window: [active-order-window.md](active-order-window.md)
