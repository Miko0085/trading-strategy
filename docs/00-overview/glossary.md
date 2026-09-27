# Глоссарий

Ниже используются русские определения с английским техническим термином в скобках.

| Термин | Простое определение |
|---|---|
| **Ордер сетки (Grid Order)** | Один логический Entry-уровень внутри Long- или Short-сетки. |
| **Настройка ордера сетки (GridOrderConfig)** | Intent конкретного уровня: Entry, sizing parameters, TP, status и связь с Grid Revision. |
| **Биржевая заявка (Exchange Order)** | Реальный ордер, отправленный на Bybit. Один GridOrderConfig может породить несколько ExchangeOrders во времени. |
| **Исполнение (Execution / Fill)** | Фактическая покупка или продажа части либо всего ExchangeOrder. Один ордер может иметь несколько fills. |
| **Заданный объём (configured_qty)** | Текущий целевой суммарный объём Grid Order: factual filled part + future remaining part. В основном Manual Grid рассчитывается системой, а не обязательно вводится вручную. |
| **Исполненный объём (filled_qty)** | Объём, который биржа фактически уже исполнила по Grid Order. Immutable factual value. |
| **Оставшийся Entry-объём (remaining_entry_qty)** | Future часть Entry, которая ещё может быть исполнена и может пересчитываться реструктуризацией. |
| **Открытый объём Strategy Lot (open_qty)** | Factual filled volume за вычетом уже закрытого объёма. |
| **Закрытый объём (closed_qty)** | Суммарный factual объём Strategy Lot, который уже закрыт. |
| **Strategy Lot / Filled Allocation** | Внутренняя атрибуция factual fills конкретного Grid Order. Появляется после первого fill, даже если Entry ещё не исполнен полностью. |
| **Частичный Take Profit (Partial TP)** | Закрытие части factual open_qty конкретного Strategy Lot. Для одного Grid Order поддерживается максимум четыре TP parts. |
| **Этап Take Profit (TP Step)** | Один из TP1–TP4: цена/процент движения и доля factual open volume. |
| **Long Grid** | Независимая сетка Entry Orders для Long. |
| **Short Grid** | Независимая сетка Entry Orders для Short. |
| **Hedge Mode** | Режим Bybit, где Long и Short по одному инструменту могут существовать одновременно. |
| **Mark Price** | Расчётная цена Bybit, используемая как factual reference для первого Entry/startup offset и risk calculations. |
| **Геометрия сетки (Grid Geometry)** | Цены и расстояния между Entry-уровнями. Не равна sizing. |
| **Sizing** | Распределение разрешённого future capital/notional между Grid Orders и перевод его в coin qty. |
| **Номинал позиции (Notional / Position Notional)** | Денежный размер позиции без деления на leverage: `price × qty`. Плановый notional обычно получается как `allocated margin × leverage`. |
| **Вес ордера (Sizing Weight)** | Относительная доля future budget до нормализации. |
| **Power Curve / Степенное распределение** | Автоматический sizing mode, где веса уровней формируются степенной кривой с коэффициентом `K`. Чем выше `K`, тем сильнее future capital смещается к дальним уровням. |
| **Per-Order M** | Advanced sizing mode: у каждого перехода между уровнями свой multiplier `M_i`; `M_i=1` означает отсутствие увеличения веса на этом переходе. |
| **Future Margin Budget** | Разрешённая маржа, которую можно распределить только между future/pending orders после учёта factual used capital и locked future capital. |
| **Future Notional Budget** | Future Margin Budget, умноженный на выбранный leverage. |
| **Active Order Window** | Число Entry Orders, которые одновременно существуют на Bybit; остальные уровни остаются queued внутри платформы. |
| **Версия сетки (Grid Revision)** | Immutable snapshot intent и sizing parameters сетки в конкретный момент. |
| **Restructuring Plan** | Предложение нового future intent/qty. Не изменяет factual history и не равно исполнению. |
| **Manual Review** | Блокирующее состояние: план нельзя исполнять автоматически до решения человека, например если один из обязательных orders не проходит биржевой минимум. |
| **Instrument Limits** | Актуальные ограничения Bybit конкретного инструмента: `minOrderQty`, `qtyStep`, `minNotionalValue`, `tickSize` и другие exchange filters. |
| **Фактическое состояние (Machine Truth)** | Что реально находится/произошло на Bybit: executions, orders, positions, wallet и т.д. |
| **Намерение трейдера (Trader Intent)** | Что трейдер настроил и собирается сделать. |
| **Объяснение трейдера (Trader Reasoning)** | Почему трейдер выбрал конкретное действие или настройку. |
| **Сверка состояния (Reconciliation)** | Сравнение expected platform state с factual Bybit state. |

Названия полей в коде/API могут оставаться английскими, но пользовательская документация должна сохранять одно и то же значение терминов.
