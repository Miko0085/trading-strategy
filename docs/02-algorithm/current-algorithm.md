# Текущий базовый алгоритм

**Статус: CONFIRMED BASE MECHANICS / OPEN DECISION LOGIC**

Этот документ описывает базовую механику, которую уже можно формализовывать технически. Он **не** утверждает, что полностью известна логика выбора параметров.

## Конфигурируемая механика

```text
START
  ↓
Select Symbol
  ↓
Configure LONG GRID
  ↓
Configure SHORT GRID
  ↓
For each Grid Order:
  - define limit price / spacing
  - define coin quantity
  - define partial TP steps
  ↓
Place / maintain configured Limit Orders
  ↓
Execution(s) occur
  ↓
Aggregate executions of source Grid Order
into Strategy Lot actual average execution price
  ↓
Track Strategy Lot independently
  ↓
Price reaches configured TP level
  ↓
Close configured % of original_qty
  ↓
Update closed_qty / remaining_qty
  ↓
Continue
```

## Что может быть автоматизировано уже на базовом уровне

Отдельный механический Execution Engine в будущем может:

- разместить заранее сконфигурированные limit orders;
- следить за фактическими executions;
- создать внутренний Strategy Lot;
- выставить/исполнить заранее заданные partial TP;
- пересчитать remaining_qty;
- принять ручное изменение конфигурации трейдера;
- отменить выбранные неисполненные orders по команде трейдера.

Это **не autonomous strategy decisioning**: параметры задаёт человек.

## Что алгоритм пока НЕ решает

- какие именно spacing выбрать;
- какой qty задать следующему ордеру;
- когда автоматически перестраивать grid;
- когда автоматически приближать TP;
- когда принудительно разгружать lot;
- какие Risk Manager thresholds использовать;
- нужен ли Stop Loss;
- как автоматически распределять капитал Long/Short.

Эти вопросы не должны блокировать реализацию самой базовой механики.
