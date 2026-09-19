# Жизненный цикл Grid

**Статус: БАЗОВАЯ ДОМЕННАЯ МОДЕЛЬ**

Grid — долговечная сущность стратегии для конкретной стороны Long или Short.

Grid не нужно путать с её конкретной версией настроек.

## Grid

Концептуальный lifecycle:

```text
CREATED
→ CONFIGURED
→ ACTIVE
→ PAUSED?        [ещё не подтверждено]
→ ENDED / CLOSED? [ещё не подтверждено]
```

Точные конечные состояния будут утверждены позже.

## Grid Revision

Каждое существенное изменение конфигурации создаёт новую immutable revision:

```text
Grid
├── Revision #1
├── Revision #2
├── Revision #3
└── ...
```

Grid Revision должна позволять восстановить:
- reference Mark Price;
- GridOrderConfig;
- configured_qty;
- TP Steps;
- active order window;
- состояние параметров до и после изменения;
- причину изменения, если она известна.

## Связь с реструктуризацией

Реструктуризация **не создаёт новую историю реальности задним числом**.

Она формирует новый `RestructuringPlan`, результатом которого после подтверждения становится новая Grid Revision.

```text
Current Grid Revision
        ↓
RestructuringPlan
        ↓
Risk Check
        ↓
Approved changes
        ↓
New Grid Revision
```

Дальше базовый Execution Engine механически исполняет уже новую Grid Revision.
