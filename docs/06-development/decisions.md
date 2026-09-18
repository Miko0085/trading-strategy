# Decision Log

Формат: Date / Decision / Status / Reason / Consequences.

---

**Date:** 2026-09-18  
**Decision:** No external indicators/news/sentiment.  
**Status:** Active  
**Reason:** Стратегия должна быть детерминированной математической системой.  
**Consequences:** Technical indicators, news, sentiment, analyst forecasts и AI price prediction не используются для торговых решений.

---

**Date:** 2026-09-18  
**Decision:** Coin quantity = primary sizing unit.  
**Status:** Active — CONFIRMED  
**Consequences:** original_qty / remaining_qty / closed_qty хранятся в монетах. Notional/margin/PnL — производные показатели.

---

**Date:** 2026-09-18  
**Decision:** Grid Orders are configurable Limit Orders.  
**Status:** Active — CONFIRMED  
**Consequences:** Spacing и qty задаются per order, без hardcoded процентов.

---

**Date:** 2026-09-18  
**Decision:** Next Grid Order may be calculated from previous configured Limit Order price.  
**Status:** Active — CONFIRMED  
**Consequences:** Для построения сетки не требуется ждать fill предыдущего уровня.

---

**Date:** 2026-09-18  
**Decision:** Executed Grid Order becomes individual Strategy Lot.  
**Status:** Active — CONFIRMED concept  
**Consequences:** Bybit aggregate position не заменяет внутренний lot accounting.

---

**Date:** 2026-09-18  
**Decision:** TP is calculated from actual average execution price of the individual Strategy Lot.  
**Status:** Active — CONFIRMED

---

**Date:** 2026-09-18  
**Decision:** Partial close percentage is based on original_qty of the individual Strategy Lot.  
**Status:** Active — CONFIRMED

---

**Date:** 2026-09-18  
**Decision:** Long and Short are separate configurable grids in Hedge Mode.  
**Status:** Active — CONFIRMED high-level mechanics  
**Consequences:** Exact parameters may differ by side and by order.

---

**Date:** 2026-09-18  
**Decision:** Base mechanical Execution Engine may be developed in parallel with strategy research.  
**Status:** Active  
**Reason:** Механика может исполнять заранее заданные трейдером параметры, не ожидая полной формализации причины выбора этих параметров.  
**Consequences:** Это не разрешает autonomous strategy decisioning и не превращает Recorder в write-enabled component.

---

**Date:** 2026-09-18  
**Decision:** Risk Manager is a later independent layer.  
**Status:** Active  
**Consequences:** Dynamic TP adaptation, forced unloading и автоматический rebalancing не входят в первую базовую механику.

---

**Date:** 2026-09-18  
**Decision:** Public documentation must not contain raw/private trading identifiers or account data.  
**Status:** Active  
**Consequences:** GitBook examples use synthetic values; real event/order IDs stay in private research data.

---

---

**Date:** 2026-09-18  
**Decision:** Strategy Recorder is permanently read-only.  
**Status:** Active — ARCHITECTURAL INVARIANT  
**Reason:** Recorder is the machine-truth / research layer and must not be able to alter the trading reality it records.  
**Consequences:** No place/amend/cancel/close/set-leverage/set-TP-SL write path may be added to `src/recorder/`. Recorder always uses a dedicated read-only Bybit key.

---

**Date:** 2026-09-18  
**Decision:** Configurable Grid Execution Engine is a separate component and may be developed in parallel with Strategy Capture.  
**Status:** Active — ARCHITECTURAL INVARIANT  
**Reason:** Mechanical execution of trader-defined parameters does not require full formalization of decision logic.  
**Consequences:** Trading/write API methods, when later enabled, live only in a separate Execution Engine with a separate API key, state, audit trail and safety controls. Recorder never imports this write path into its runtime responsibility.

---

## Knowledge rule

Не превращать EXAMPLE / TRADER EXPLANATION / CANDIDATE в CONFIRMED RULE без явного подтверждения трейдера.
