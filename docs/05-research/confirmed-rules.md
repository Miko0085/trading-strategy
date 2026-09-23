# Подтверждённые правила

**Статус: ПОДТВЕРЖДЕНО**

## 1. Основной рабочий режим — Manual Grid

На текущем этапе основная стратегия строится не через Veles-like автогенератор диапазона, а через ручную настройку уровней Long/Short.

Generated Grid остаётся дополнительной функцией/конструктором и не определяет основной workflow MVP.

## 2. Grid Orders — лимитные ордера

Каждый Grid Order является лимитной Entry-заявкой.

## 3. Long и Short — независимые сетки

Они могут использовать разные уровни, allocation, active window, per-order Martingale и TP-настройки.

## 4. Первый Entry привязан к Mark Price при запуске

При запуске фиксируется текущая Mark Price.

- Long: первый Entry располагается ниже Mark Price на заданный startup offset.
- Short: первый Entry располагается выше Mark Price на заданный startup offset.

## 5. Уровни сетки задаёт трейдер вручную

Для каждого будущего Grid Order трейдер может задавать:
- абсолютную Entry Price;
- либо процентный отступ.

Для #1 процент относится к reference/Mark Price. Для #2+ процент может задаваться относительно предыдущего уровня.

## 6. Геометрия и sizing разделены

```text
Grid Geometry = где находятся уровни
Grid Sizing   = какой объём получает каждый уровень
```

Изменение sizing не должно автоматически менять цены уровней.

## 7. Qty в основном Manual Grid рассчитывает система

Трейдер задаёт allocation стороны, leverage, цены уровней и Martingale-параметры.

Система рассчитывает `configured_qty` на основании:
- доступного бюджета стороны;
- уже фактически использованного капитала;
- цен уровней;
- leverage;
- per-order Martingale chain;
- Bybit `qtyStep`, `minOrderQty`, `minNotionalValue`.

## 8. Martingale задаётся индивидуально на каждый ордер

Коэффициент конкретного ордера является множителем относительно предыдущего веса.

```text
w1 = 1
w2 = w1 × M2
w3 = w2 × M3
...
wn = w(n-1) × Mn
```

Пример:

```text
M2 = 1.20
M3 = 1.50

w1 = 1.00
w2 = 1.20
w3 = 1.80
```

Полученные cumulative weights затем нормализуются на доступный future budget стороны.

## 9. Active Order Window обязателен

Полная логическая сетка может содержать больше уровней, чем одновременно размещено на Bybit.

Трейдер задаёт `active_order_count`, например 3, 4 или 5. По мере исполнения активного Entry следующий queued level занимает освободившееся место.

## 10. Один Grid Order может иметь несколько fills

Несколько executions не создают несколько Grid Orders.

## 11. Factual filled volume immutable

После фактического исполнения уже набранный объём нельзя уменьшать или перераспределять как будто сделки не было.

Пересчитываться может только future/pending часть:

```text
configured_qty >= filled_qty
remaining_entry_qty = configured_qty - filled_qty
```

## 12. Реструктуризация объёма поддерживает два scope

Подтверждены два ручных действия:

```text
RECALCULATE_ORDER
RECALCULATE_GRID
```

### RECALCULATE_ORDER

Пересчитывается future qty выбранного Grid Order в пределах доступного бюджета стороны. Остальные уровни не должны автоматически изменяться.

### RECALCULATE_GRID

Весь оставшийся future budget стороны перераспределяется между всеми eligible pending levels по текущей per-order Martingale chain.

## 13. Добавление нового уровня допускает перерасчёт

После добавления нового Grid Order трейдер может:
- рассчитать только новый ордер;
- либо перераспределить future budget по всей оставшейся сетке.

## 14. Factual used capital учитывается до перераспределения

Общая логика:

```text
Side Budget
- Factual Used Capital
- Locked Future Capital
= Available Future Budget
```

Только этот future budget может перераспределяться между pending levels.

## 15. Take Profit считается от фактического исполнения

TP конкретного StrategyLot рассчитывается от его factual average fill и factual open qty.

Если Entry исполнен частично, TP относится только к фактически исполненному объёму.

## 16. Take Profit — лимитный

Обычный TP реализуется лимитными закрывающими заявками.

## 17. Биржевые минимумы берутся с Bybit

Перед планированием/размещением используются актуальные:
- `minOrderQty`;
- `qtyStep`;
- `minNotionalValue`;
- `tickSize`.

## 18. Изменения конфигурации создают Grid Revision

Существенные изменения intent должны быть доступны в before/after audit и новой immutable revision.

## 19. Внешнее ручное вмешательство не запускает скрытую перестройку

Если factual Bybit state отличается от ожидаемого, система должна показать расхождение и потребовать подтверждение Adopt/Restore.

## 20. Внешние сигналы не используются

Стратегия не использует новости, sentiment, технические индикаторы, прогнозы, мнения аналитиков или AI price prediction.

## 21. Generated Grid остаётся дополнительным режимом

Подтверждённая normalized power distribution и глобальный geometric martingale для Generated Grid не удаляются, но относятся только к optional/legacy constructor и не являются основной моделью Manual Grid MVP.
