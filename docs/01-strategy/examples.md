# Примеры механики

Публичная документация использует только **синтетические примеры**. Реальные order IDs, приватные trade dumps и данные аккаунта не должны публиковаться здесь.

## Пример 1 — построение Long Grid

```text
Reference Price = 100

Order #1
Limit = 90
Qty = 100 coins

Order #2
-5% from previous limit
Limit = 85.50
Qty = 150 coins

Order #3
-3% from previous limit
Limit = 82.935
Qty = 220 coins
```

Числа — демонстрационные. Из примера нельзя выводить sizing formula.

## Пример 2 — Strategy Lot после исполнения

Допустим Grid Order фактически исполнился несколькими fills и его actual average execution price составил 80.

```text
original_qty = 1000 coins
actual_average_execution_price = 80
remaining_qty = 1000
```

С этого момента исполненный объём отслеживается как отдельный Strategy Lot.

## Пример 3 — partial TP

```text
Lot entry = 80
original_qty = 1000

TP1 = +5% from lot entry
close = 10% of original_qty = 100 coins

TP2 = +7% from lot entry
close = 20% of original_qty = 200 coins
```

TP2 также считается от entry = 80, а не от TP1.

После двух исполнений:

```text
closed_qty = 300
remaining_qty = 700
```

## Пример 4 — глубокий lot и небольшой rebound

**TRADER EXPLANATION:** более глубокий Grid Order может иметь более выгодную цену входа. Поэтому при небольшом rebound такой lot способен выйти в прибыль раньше всей агрегированной позиции и быть частично разгружен.

Это объясняет смысл механики, но не задаёт универсальный процент rebound или partial close.
