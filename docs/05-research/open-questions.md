# Открытые вопросы

**Статус: ОТКРЫТЫЕ ВОПРОСЫ ПО НЕПОДТВЕРЖДЁННОЙ АВТОМАТИКЕ И CAPITAL SEMANTICS**

Подтверждённые правила Manual Grid, per-order Martingale и ручного volume restructuring отсюда удалены. Здесь остаются только реально нерешённые вопросы.

## Base Grid / Execution

1. Как синхронизировать TP при новых partial fills одного Entry Grid Order: amend существующих TP или создавать дополнительные?
2. Когда именно partial-filled Entry должен освобождать слот Active Order Window: после первого fill, полного fill или по отдельному правилу?
3. Какая runtime-политика нужна для cancel/amend оставшейся части partial-filled Entry после restructuring?

## Capital Base

4. Какое точное factual поле/формула является production `capital_base`?
5. Как исключить двойной учёт realized/unrealized PnL при расчёте Effective Side Budget?
6. Как формально применяется reserve при разных режимах cross margin?
7. Какие factual margin fields являются authoritative для уже использованного капитала на конкретном типе Bybit account?

## Automatic Restructuring

8. Какие события должны автоматически запускать `RECALCULATE_ORDER` или `RECALCULATE_GRID`?
9. Нужен ли cooldown/debounce между автоматическими перерасчётами?
10. Какие изменения allocation могут происходить автоматически, если вообще могут?
11. Когда нужен полный rebase geometry на новую reference price?
12. Когда начинается новый Grid Cycle вместо новой revision текущего cycle?

## Reinvestment / Recovery

13. Какая доля realized profit автоматически добавляется к будущему budget?
14. Должен ли unrealized PnL участвовать в production sizing, и если да — по какой подтверждённой формуле?
15. Какой объём восстанавливать после прибыльной разгрузки?
16. На каком уровне/условии создавать recovery order?
17. Recovery должен быть отдельным ордером или частью общего `RECALCULATE_GRID`?

## Trailing

18. Какой trigger двигает pending geometry?
19. Trailing работает непрерывно или дискретными шагами?
20. Что делать с вручную зафиксированными Entry/TP fields при trailing?

## Strategy Capital / Risk

21. Какой минимальный рабочий капитал нужен для запуска конкретной сетки сверх биржевых минимумов?
22. Какие margin/equity/exposure limits должен применять Risk Manager?
23. Какой минимальный reserve обязателен?
24. Какие emergency actions разрешены Risk Manager?
25. Когда Risk Manager должен ALLOW / MODIFY / DENY?

## Bybit semantics, которые нужно проверить фактически

26. Семантика `execPnl` и fees для расчёта net realized PnL.
27. Точное поведение position/account fields для используемого account mode.
28. Поведение amend/cancel/replace при частично исполненном Entry в будущей write-интеграции.

Эти вопросы нельзя заполнять предположениями.
