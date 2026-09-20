import { describe, expect, it } from "vitest";
import { formatAuditDiff, humanAction } from "./auditFormat";

describe("audit formatting", () => {
  it("uses human labels for all supported actions", () => {
    expect(humanAction("revision_saved")).toBe("Сохранена версия");
    expect(humanAction("grid_order_added")).toBe("Добавлен уровень");
    expect(humanAction("grid_order_deleted")).toBe("Удалён уровень");
    expect(humanAction("note_changed")).toBe("Изменена заметка");
  });

  it("formats allocation and order changes without raw JSON", () => {
    expect(formatAuditDiff({ long_pct: 40, reserve_pct: 40 }, { long_pct: 45, reserve_pct: 35 }, "allocation_changed")).toEqual(["Лонг: 40 → 45", "Резерв: 40 → 35"]);
    expect(formatAuditDiff({ qty: 0.2 }, { qty: 0.35 }, "grid_order_qty_changed")).toEqual(["Объём: 0.2 → 0.35"]);
    expect(formatAuditDiff({ note: "old" }, { note: "new" }, "note_changed")).toEqual(["Было: old", "Стало: new"]);
  });

  it("formats modified, added and removed TP steps", () => {
    expect(formatAuditDiff([{ move_pct: 2, close_pct: 25 }], [{ move_pct: 3, close_pct: 40 }], "tp_changed")).toEqual(["TP 1", "Движение: 2 → 3", "Закрыть: 25 → 40"]);
    expect(formatAuditDiff([], [{ move_pct: 4, close_pct: 25 }], "tp_changed")).toEqual(["TP 1 добавлен", "Движение: 4", "Закрыть: 25"]);
    expect(formatAuditDiff([{ move_pct: 4, close_pct: 25 }], [], "tp_changed")).toEqual(["TP 1 удалён", "Движение: 4", "Закрыть: 25"]);
  });
});
