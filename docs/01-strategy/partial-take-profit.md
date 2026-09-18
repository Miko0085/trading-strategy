# Partial Take Profit

**Статус: CONFIRMED (правило расчёта) / EXPERIMENTAL (конкретные уровни)**

## CONFIRMED RULE

Partial TP индивидуален для каждого Strategy Lot. Все TP конкретного lot считаются **относительно ACTUAL AVERAGE EXECUTION PRICE этого lot**.

Явно **не** относительно:

- общей average entry всей Long-позиции;
- общей average entry всей Short-позиции;
- предыдущего TP;
- начальной цены рынка на момент построения сетки.

### Пример

```
Lot entry = 0.40

TP1 = +5% от 0.40
TP2 = +7% от 0.40
TP3 = +10% от 0.40
```

Конкретные проценты (`+5% / +7% / +10%`) — иллюстрация, не подтверждённые уровни.

## Partial unloading — механика закрытия

**Close percentage считается от `original_qty` конкретного lot**, а не от текущего remaining_qty.

```
original_qty = 1000 LSK

TP1: close 25% → 250
TP2: close 25% → ещё 250

Remaining: 500
```

Второй `25%` **не** считается от оставшихся `750` — это была бы другая (компаундная) модель. Модель должна поддерживать список этапов `take_profit_steps[]` (0..N), минимально с полями:

- `distance_from_lot_entry_pct`
- `close_pct_of_original_qty`
- `close_qty`

## Partial unloading — смысл (TRADER EXPLANATION)

При глубоком заполнении grid последние lots могут иметь более выгодную цену входа. При небольшом rebound/коррекции они раньше выходят в прибыль. Трейдер использует partial unloading, чтобы:

- фиксировать realized PnL;
- высвобождать margin;
- возвращать available balance;
- продолжать торговлю.

Исторический пример (со слов трейдера, без ID в Recorder-датасете): ETH Short разгружался частями на коррекциях. Это описание мотива, **не** универсальная математическая формула — см. [05-research/candidate-rules.md](../05-research/candidate-rules.md).

## Наблюдение на реальных данных

На UAIUSDT (первый цикл, см. [examples.md](examples.md)) закрытие было **полным** (151 → 0 одним ордером), партиальных закрытий пока не наблюдалось ни разу. Правило про partial unloading выше сформулировано трейдером как общий принцип, но ещё не проверено на конкретном закрытом lot из dataset.
