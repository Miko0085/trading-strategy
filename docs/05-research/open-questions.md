# Открытые вопросы

## Geometry

1. Какая точная математическая функция distribution coefficient?
2. Как нормализовать глубину так, чтобы последний уровень точно соответствовал configured depth?
3. Когда создаётся новая Geometry, а когда достаточно сдвинуть anchor?

## Dynamic Sizing

4. Какая точная формула перераспределения side budget между оставшимися уровнями?
5. Как Martingale curve масштабируется после изменения capital base?
6. Какие конкретные Bybit account fields являются canonical capital base?
7. Как учитывать funding и fees?

## Partial fills / TP

8. При новых fills amend существующие TP или создавать дополнительные?
9. Как округлять TP qty по qtyStep и куда относить residual?
10. Что делать с Entry configured_qty, если target меняется после partial fill?

## Recovery

11. Какой exact qty восстанавливать после unload?
12. Recovery связан с конкретным sold lot или с общим inventory?
13. Как рассчитывается recovery price/distance?

## Trailing

14. Что является trigger?
15. Какой trailing step?
16. Непрерывный или дискретный trailing?
17. Можно ли двигать уже выставленные, но неисполненные ExchangeOrders, или только queued levels?

## Risk

18. Какой минимальный Reserve обязателен?
19. Какие account-level exposure/drawdown/liquidation-buffer limits?
20. Какие emergency actions разрешены Risk Manager?
