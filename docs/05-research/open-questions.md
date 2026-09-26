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

8. Должно ли исполнение любого прибыльного TP / profitable close автоматически запускать full-grid recalculation или только создавать restructuring proposal?
9. Нужен ли cooldown/debounce между автоматическими перерасчётами при серии TP/fills?
10. Должен ли trigger Long по умолчанию реинвестировать только в Long, trigger Short — только в Short?
11. Если разрешён cross-side reinvestment, по какой формуле определяется приоритет Long против Short?
12. Может ли расстояние Mark Price до factual average Long/Short быть одним из primary risk factors, или обязательно использовать liquidation/margin metrics?
13. Сохраняются ли базовые Long/Short allocation percentages при reinvestment или допускается временное динамическое отклонение?
14. Допустимо ли распределять новый reinvestable capital сразу между обеими сторонами?
15. Что делать, если распределение между всеми нужными сторонами/уровнями создаёт хотя бы один order ниже Bybit min lot/notional?
16. Когда нужен полный rebase geometry на новую reference price?
17. Когда начинается новый Grid Cycle вместо новой revision текущего cycle?

## Reinvestment / Recovery

18. Что именно реинвестируется после прибыльного закрытия: только net realized profit или весь released capital + profit?
19. Какая доля reinvestable capital автоматически добавляется к future budget?
20. Должен ли unrealized PnL участвовать в production sizing, и если да — по какой подтверждённой формуле?
21. Какой объём восстанавливать после прибыльной разгрузки?
22. На каком уровне/условии создавать recovery order?
23. Recovery должен быть отдельным ордером или частью общего `RECALCULATE_GRID`?
24. Какой минимальный reinvestment имеет смысл, чтобы не дробить капитал на технически неисполняемые ордера?
25. Если valid restructuring возможен только для одной стороны, допускается ли временно направить весь reinvestable capital только туда?

## Trailing

26. Какой trigger двигает pending geometry?
27. Trailing работает непрерывно или дискретными шагами?
28. Что делать с вручную зафиксированными Entry/TP fields при trailing?

## Strategy Capital / Risk

29. Какой минимальный рабочий капитал нужен для запуска конкретной сетки сверх биржевых минимумов?
30. Какие margin/equity/exposure limits должен применять Risk Manager?
31. Какой минимальный reserve обязателен?
32. Какие emergency actions разрешены Risk Manager?
33. Когда Risk Manager должен ALLOW / MODIFY / DENY?

## Bybit semantics, которые нужно проверить фактически

34. Семантика `execPnl` и fees для расчёта net realized PnL.
35. Точное поведение position/account fields для используемого account mode.
36. Поведение amend/cancel/replace при частично исполненном Entry в будущей write-интеграции.
37. Как часто refreshить instrument limits и какой freshness threshold обязателен перед PLACE/AMEND/restructuring validation?

## Safety rule уже не является открытым вопросом

Если новый restructuring plan содержит хотя бы один обязательный order, который после нормализации не проходит актуальные Bybit `minOrderQty`, `qtyStep`, `minNotionalValue` или price `tickSize`, план не применяется частично. Он переводится в `MANUAL_REVIEW` и требует нового расчёта/решения.

Подробное исследование routing logic: `reinvestment-routing-research.md`.

Эти вопросы нельзя заполнять предположениями.