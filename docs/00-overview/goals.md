# Цели

**Статус: TRADER EXPLANATION / FUTURE**

## Текущая цель (Phase 1 — Base Strategy Mechanics)

Формализовать реальную механику ручной торговли трейдера:

- Long / Short в Hedge Mode;
- Grid Orders (сетки лимитных ордеров);
- coin quantity как единица учёта;
- order spacing (расстояние между уровнями сетки);
- независимые Strategy Lots;
- partial Take Profit;
- partial unloading (частичная разгрузка позиции);
- order lifecycle и grid lifecycle;
- ручное изменение параметров трейдером.

## Дальнейшие цели (не текущий этап)

| Фаза | Содержание |
|---|---|
| Phase 2 | Formalization / Testing — превращение подтверждённых правил в проверяемый алгоритм |
| Phase 3 | Risk Manager — контроль капитала/margin/exposure (не предсказание рынка) |
| Phase 4 | Дополнительные internal managers/helpers |

Подробный roadmap: [06-development/roadmap.md](../06-development/roadmap.md).

## Не цели

- Не создать индикаторного/сигнального робота.
- Не автоматизировать реальные ордера на этом этапе.
- Не предсказывать рынок и не оптимизировать стратегию "от себя" — см. [principles.md](principles.md).
