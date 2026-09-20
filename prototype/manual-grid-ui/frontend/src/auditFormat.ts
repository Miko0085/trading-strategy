import { AuditPayload } from "./types";

const ACTIONS: Record<string, string> = {
  revision_saved: "Сохранена версия",
  grid_order_added: "Добавлен уровень",
  grid_order_deleted: "Удалён уровень",
  grid_order_qty_changed: "Изменён объём ордера",
  grid_order_offset_changed: "Изменён отступ",
  note_changed: "Изменена заметка",
  allocation_changed: "Изменено распределение капитала",
  tp_changed: "Изменён тейк-профит",
};

const LABELS: Record<string, string> = {
  long_pct: "Лонг",
  short_pct: "Шорт",
  reserve_pct: "Резерв",
  qty: "Объём",
  offset_pct: "Отступ",
  move_pct: "Движение",
  close_pct: "Закрыть",
};

function record(value: AuditPayload | undefined): Record<string, unknown> | null {
  return value !== null && !Array.isArray(value) && typeof value === "object" ? value as Record<string, unknown> : null;
}

function array(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return "нет данных";
  return String(value);
}

function field(value: Record<string, unknown>, key: string): unknown {
  const camel = key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
  return value[key] ?? value[camel];
}

function changed(before: Record<string, unknown>, after: Record<string, unknown>, key: string): string | null {
  return field(before, key) !== field(after, key) ? `${LABELS[key] ?? key}: ${display(field(before, key))} → ${display(field(after, key))}` : null;
}

function tpLines(before: unknown[], after: unknown[]): string[] {
  const lines: string[] = [];
  const count = Math.max(before.length, after.length);
  for (let index = 0; index < count; index += 1) {
    const oldTp = record(before[index] as AuditPayload);
    const newTp = record(after[index] as AuditPayload);
    if (!oldTp && newTp) {
      lines.push(`TP ${index + 1} добавлен`, `Движение: ${display(field(newTp, "move_pct"))}`, `Закрыть: ${display(field(newTp, "close_pct"))}`);
    } else if (oldTp && !newTp) {
      lines.push(`TP ${index + 1} удалён`, `Движение: ${display(field(oldTp, "move_pct"))}`, `Закрыть: ${display(field(oldTp, "close_pct"))}`);
    } else if (oldTp && newTp) {
      const move = changed(oldTp, newTp, "move_pct");
      const close = changed(oldTp, newTp, "close_pct");
      if (move || close) lines.push(`TP ${index + 1}`, ...(move ? [move] : []), ...(close ? [close] : []));
    }
  }
  return lines;
}

export function humanAction(action: string): string {
  return ACTIONS[action] ?? "Изменение конфигурации";
}

export function formatAuditDiff(before: AuditPayload | undefined, after: AuditPayload | undefined, action?: string): string[] {
  if (action === "tp_changed") return tpLines(array(before), array(after));
  const oldRecord = record(before);
  const newRecord = record(after);
  if (!oldRecord || !newRecord) {
    if (action === "grid_order_added" && newRecord) return [`Уровень ${display(field(newRecord, "level"))} · Объём: ${display(field(newRecord, "qty"))} · Отступ: ${display(field(newRecord, "offset_pct"))}`];
    if (action === "grid_order_deleted" && oldRecord) return [`Уровень ${display(field(oldRecord, "level"))} · Объём: ${display(field(oldRecord, "qty"))} · Отступ: ${display(field(oldRecord, "offset_pct"))}`];
    return [];
  }
  if (action === "note_changed") return [`Было: ${display(field(oldRecord, "note"))}`, `Стало: ${display(field(newRecord, "note"))}`];
  const keys = action === "allocation_changed" ? ["long_pct", "short_pct", "reserve_pct"] : ["qty", "offset_pct", "note", "move_pct", "close_pct"];
  return keys.map((key) => changed(oldRecord, newRecord, key)).filter((line): line is string => line !== null);
}
