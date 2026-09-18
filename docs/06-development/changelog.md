# Changelog (docs/)

Изменения в этой документации (не в коде Recorder'а — для кода см. корневой [`DEVELOPMENT_STATUS.md`](../../DEVELOPMENT_STATUS.md)).

## 2026-09-18

- Создана структура `docs/` как канонический слой стратегической/платформенной документации: `00-overview/` … `06-development/`.
- Зафиксирован главный принцип «без внешних сигналов» как project-wide правило ([00-overview/principles.md](../00-overview/principles.md)).
- Перенесены и структурированы наблюдения по UAIUSDT из `STRATEGY_KNOWLEDGE.md` в [05-research/](../05-research/trader-observations.md) и [01-strategy/examples.md](../01-strategy/examples.md).
- Зафиксировано противоречие `CONTRADICTION-01` (глубина сетки "-30% от входа" не воспроизвелась во втором цикле).
- Добавлен `.gitbook.yaml` (root: `./docs/`) и `docs/SUMMARY.md` для GitBook Git Sync.
- Инициализирован git-репозиторий, сделан первый коммит.
