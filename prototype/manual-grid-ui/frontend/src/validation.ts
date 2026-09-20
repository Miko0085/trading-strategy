export function translateValidation(error: string): string {
  let match = error.match(/^qty must be >= (.+)$/);
  if (match) return `Минимальный объём: ${match[1]}`;
  match = error.match(/^qty must respect qty_step (.+)$/);
  if (match) return `Объём должен быть кратен шагу: ${match[1]}`;
  match = error.match(/^notional must be >= (.+)$/);
  if (match) return `Минимальная стоимость ордера: ${match[1]}`;
  if (error === "TP close_pct total must be <= 100") return "Суммарный объём закрытия TP превышает 100%";
  if (error === "full grid exceeds allocation limit") return "Полная сетка превышает выделенный лимит";
  if (error.includes("active_count")) return "Некорректное количество активных уровней";
  if (error === "offset_pct must be > 0") return "Отступ должен быть больше 0%";
  if (error === "move_pct must be > 0") return "TP должен быть больше 0%";
  if (error === "close_pct must be between 0 and 100") return "Процент закрытия TP должен быть от 0 до 100%";
  return "Параметр конфигурации заполнен неверно";
}
