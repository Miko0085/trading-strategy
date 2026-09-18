# Decision Log

Формат записи: Date / Decision / Status / Reason / Consequences.

---

**Date:** 2026-09-18
**Decision:** No external indicators/news/sentiment.
**Status:** Active
**Reason:** Стратегия — детерминированная математическая система на основе цены и состояния аккаунта (см. [00-overview/principles.md](../00-overview/principles.md)).
**Consequences:** RSI/MACD/MA/Bollinger/Stochastic, новости, sentiment, AI-прогнозы не используются нигде в базовой стратегии и в будущем Risk Manager.

---

**Date:** 2026-09-18
**Decision:** Coin quantity = primary sizing unit.
**Status:** Active
**Reason:** USDT notional/margin/PnL — производные величины, а не основа расчётов объёма.
**Consequences:** Все формулы объёма (grid sizing, partial close) выражаются в coin quantity, не в долларах.

---

**Date:** 2026-09-18
**Decision:** Grid spacing configurable per order.
**Status:** Active
**Reason:** Конкретные проценты — предмет настройки/эксперимента, не хардкода.
**Consequences:** Будущая реализация не должна фиксировать проценты spacing в коде как константы.

---

**Date:** 2026-09-18
**Decision:** Next Grid Order price can be calculated from previous Limit Order price.
**Status:** Active
**Reason:** Наблюдаемый механизм построения сетки; не требует ожидания fill предыдущего уровня.
**Consequences:** Grid можно строить полностью заранее, не дожидаясь исполнений.

---

**Date:** 2026-09-18
**Decision:** Executed Grid Order becomes individual Strategy Lot.
**Status:** Active (концептуально; таблиц в БД пока нет)
**Reason:** Bybit агрегирует позицию, но независимый учёт нужен для корректного partial TP.
**Consequences:** Требует будущей модели данных отдельно от текущей схемы Recorder'а (см. [04-platform/data-model.md](../04-platform/data-model.md)).

---

**Date:** 2026-09-18
**Decision:** TP calculated from individual Lot execution price.
**Status:** Active — CONFIRMED
**Reason:** Явно сформулировано как правило (не относительно общей average entry, не относительно предыдущего TP).
**Consequences:** См. [05-research/confirmed-rules.md](../05-research/confirmed-rules.md).

---

**Date:** 2026-09-18
**Decision:** Partial close percentage based on original lot quantity.
**Status:** Active — CONFIRMED
**Reason:** Второй этап TP не должен пересчитываться от уже уменьшенного remaining_qty.
**Consequences:** См. [01-strategy/partial-take-profit.md](../01-strategy/partial-take-profit.md).

---

**Date:** 2026-09-18
**Decision:** Risk Manager postponed until base mechanics are formalized.
**Status:** Active
**Reason:** Сначала механика и подтверждённые правила, потом автоматизация решений о риске.
**Consequences:** Phase 3 не начинается раньше значимого прогресса в Phase 1–2 (см. [roadmap.md](roadmap.md)).

---

**Date:** 2026-09-18
**Decision:** `docs/` is the canonical strategy/public documentation directory.
**Status:** Active
**Reason:** Нужен единый, версионируемый, публикуемый через GitBook слой документации, отдельный от кода Recorder'а. Отдельная папка `docx/` не создавалась — используется уже существующая `docs/` (переименование пустой заготовки), чтобы не плодить два похожих каталога.
**Consequences:** Все новые стратегические/платформенные документы добавляются в `docs/`, не в корень репозитория и не в новую папку.

---

## Правило ведения этого журнала

Никогда не помечать пункт как `CONFIRMED` в [05-research/confirmed-rules.md](../05-research/confirmed-rules.md), если явное подтверждение трейдера отсутствует. Решения об архитектуре документации (как записи выше) — это решения владельца проекта, а не торговые правила, и фиксируются здесь отдельно от `05-research/`.
