# Risk Register

**Статус: OPEN QUESTION / FUTURE**

Реестр известных источников риска в текущей ручной практике. Это не формулы и не пороги — только перечень того, что нужно будет учитывать будущему Risk Manager (см. [future-risk-manager.md](future-risk-manager.md)).

| Риск | Статус | Комментарий |
|---|---|---|
| Отсутствие Stop Loss | `EXPERIMENTAL / OPEN QUESTION` | См. [known-risks.md](known-risks.md) |
| Неограниченная глубина grid | `OPEN QUESTION` | Hard limit на число ордеров сознательно не задаётся (см. [01-strategy/grid-mechanics.md](../01-strategy/grid-mechanics.md)) |
| Рост объёма глубже по сетке | `CANDIDATE` | Увеличивает используемую маржу при движении против позиции; точный sizing не подтверждён |
| Long/Short capital allocation | `OPEN QUESTION` | Формального правила распределения капитала между сторонами нет |
| Margin utilization при одновременных Long+Short | `OPEN QUESTION` | Пороги не определены |
| Combined break-even Long+Short | `OPEN QUESTION` | Формула не выведена |

Полный список открытых вопросов — [05-research/open-questions.md](../05-research/open-questions.md).
