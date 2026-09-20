import { describe, expect, it } from "vitest";
import { historyItems } from "./revisionHistory";

describe("revision history identity", () => {
  it("matches comments by revision entity id, not array order", () => {
    const events = [
      { created_at: "2026-01-02", action: "revision_saved", entity_type: "grid_revision", entity_id: "rev-b" },
      { created_at: "2026-01-01", action: "revision_saved", entity_type: "grid_revision", entity_id: "rev-a" },
    ];
    const result = historyItems(events, [
      { id: "rev-a", symbol: "BTCUSDT", comment: "first", validation_state: "VALID", created_at: "2026-01-01" },
      { id: "rev-b", symbol: "BTCUSDT", comment: "second", validation_state: "VALID", created_at: "2026-01-02" },
    ]);
    expect(result.map((item) => item.comment)).toEqual(["second", "first"]);
  });
});
