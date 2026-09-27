# Открытые вопросы

**Статус: OPEN — CAPITAL ROUTING, RISK, RECOVERY И EXECUTION EDGE CASES**

Sizing modes `POWER_CURVE` и `PER_ORDER_M`, максимум 4 TP parts, factual fill immutability и atomic minimum-lot guard больше не являются открытыми вопросами.

## Capital Base

1. Какое factual поле/формула является production `capital_base`?
2. Как исключить double counting realized/unrealized PnL?
3. Что именно считается reinvestable capital после profitable TP: net realized profit или released capital + profit?
4. Как reserve применяется в cross margin?
5. Какие margin fields authoritative для factual used capital?

## Reinvestment Routing

6. Базовый routing: same-side, cross-side risk-priority или обе стороны?
7. Если cross-side — какая формула задаёт приоритет?
8. Достаточно ли distance Mark→LongAvg/ShortAvg или обязательны liquidation/margin metrics?
9. Сохраняются ли базовые Long/Short allocation percentages после reinvestment?
10. Допустимо ли временное отклонение от allocation ради safety?
11. Что делать, если новый capital достаточен для minimum lot только одной стороны?

## Automatic Restructuring

12. Profitable TP уже является trigger для нового proposal. Должен ли proposal автоматически применяться после Risk Check или пока требовать подтверждение?
13. Нужен ли cooldown/debounce при серии TP/fills?
14. Как дедуплицировать повторный trigger одного factual execution?
15. Когда full-grid recalculation создаёт новую Grid Cycle, а когда только Revision?

## Recovery / Trailing

16. Нужен ли отдельный recovery order после TP или достаточно общего `RECALCULATE_GRID`?
17. Какой trigger двигает pending Geometry?
18. Trailing непрерывный или дискретный?
19. Когда нужен полный rebase на новую Mark Price?

## TP / Partial Fill

20. Если Entry получает новые fills после выставления TP, amend существующие TP или перераспределять qty в рамках максимум четырёх TP parts?
21. Когда partial-filled Entry освобождает слот Active Order Window?
22. Какая cancel/amend policy применяется к remaining Entry после restructuring?

## Risk Manager

23. Какой minimum reserve обязателен?
24. Как измерять допустимый liquidation distance?
25. Какие max exposure limits нужны?
26. При каких условиях ALLOW / MODIFY / DENY?
27. Какие emergency actions разрешены?
28. Нужны ли hard limits для `K` и `M_i` или достаточно exposure/risk limits?

## Bybit Production Semantics

29. Точная semantics account/margin fields для используемого UTA/cross-margin mode.
30. `execPnl`, fees и funding для net realized PnL.
31. Поведение amend/cancel/replace partially-filled Entry.
32. Freshness policy InstrumentSpec перед PLACE/AMEND.

Эти вопросы нельзя закрывать предположениями.
