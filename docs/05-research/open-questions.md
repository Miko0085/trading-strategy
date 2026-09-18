# Open Questions

**Статус: OPEN QUESTION**

## Приоритет: Base Strategy Mechanics

1. Как определяется `original_qty` каждого следующего Grid Order?
2. Есть ли математическая функция изменения spacing по глубине или все уровни задаются вручную?
3. Как определяется стартовая/reference price для нового Grid?
4. Когда трейдер отменяет ещё не исполненные Grid Orders?
5. Когда и как вручную перестраивается оставшаяся сетка?
6. Что происходит с `remaining_qty`, если сумма planned partial TP меньше 100%?
7. Есть ли обязательный final TP?
8. Нужен ли Stop Loss в базовой hedge-механике?
9. Какие параметры Short Grid отличаются от Long Grid и почему?
10. Есть ли формальное правило повторного запуска нового grid cycle?

## Формализация Long / Short

11. Как формально задаётся Long/Short capital allocation?
12. Как рассчитывается combined Long/Short break-even zone?
13. Какова точная формула использования положительного Short uPnL как расчётной базы для добавления Long?
14. Существует ли симметричное правило Long uPnL -> добавление Short?

## Позднее: Risk Manager

15. Какие показатели margin/equity должны отслеживаться?
16. Какие thresholds считаются warning / critical?
17. При каких условиях TP автоматически приближается?
18. Как выбирается lot для ранней разгрузки?
19. Допустимо ли автоматическое закрытие около break-even ради восстановления available margin?
20. Какие hard limits нужны по gross exposure, side exposure и margin utilization?

Risk Manager вопросы сохраняются здесь, но **не должны блокировать Base Strategy Mechanics**.
