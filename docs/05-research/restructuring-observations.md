# Наблюдения по реструктуризации

**Статус: RESEARCH / STRATEGY CAPTURE**

## Что записывать на каждом trigger

STATE BEFORE → TRIGGER EVENT → FRESH ACCOUNT STATE → ALLOCATION SNAPSHOT → DECISION → GRID REVISION → EXCHANGE REALITY → STATE AFTER.

## State Before

Нужно фиксировать symbol, Position Mode, Long/Short sizes, Strategy Lots, realized/unrealized PnL, available capital fields, Long/Short/Reserve percentages, Grid Geometry, anchor, sizing policy, pending/active orders и TP orders.

## Trigger

Фиксировать Entry partial/full fill, TP partial/full fill, manual close, capital change, trailing trigger и manual strategy edit.

## Что менялось

Отдельно записывать:
- geometry changed?;
- anchor changed?;
- qty changed? какие уровни;
- allocation changed?;
- keep/cancel/amend/create;
- recovery action;
- reason.

## Главная исследовательская цель

Не смешивать Dynamic Sizing, Grid Positioning/Trailing и Volume Recovery. Для каждого повторяющегося события нужно понимать, какой именно механизм сработал.
