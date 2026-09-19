# Открытые вопросы

**Статус: ОТКРЫТЫЙ ВОПРОС**

## Base Grid / Execution

1. Как синхронизировать TP при новых partial fills одного Entry Grid Order: amend существующих TP или создавать дополнительные?
2. Можно ли менять configured_qty входного Grid Order после первого fill?

## Restructuring Algorithm

3. Что именно является trigger реструктуризации?
4. Что входит в capital_base перед новым перерасчётом?
5. Как формально работает compound allocation?
6. Как задаётся margin reserve?
7. Какой объём восстанавливать после прибыльной разгрузки: тот же coin qty или объём на весь освобождённый капитал?
8. На каком расстоянии/условии выставлять recovery order?
9. Когда оставить существующие pending orders, а когда перестроить их?
10. Когда происходит полный rebase на новую Mark Price?
11. Когда текущая Grid Revision продолжается, а когда начинается новый Grid cycle?
12. Как учитывать realized PnL?
13. Использовать ли unrealized PnL в capital_base?
14. Как формально задаётся Long / Short capital allocation?

## Strategy Capital

15. Какой минимальный капитал стратегии нужен для запуска одной монеты сверх биржевого minOrderQty/minNotionalValue?

## Future Risk Manager

16. Какие margin/equity/exposure limits использовать?
17. Какой минимальный margin reserve обязателен?
18. Когда Risk Manager должен ALLOW / MODIFY / DENY?
19. Какие emergency actions разрешены?

Эти вопросы нельзя заполнять предположениями.