export function money(value: number | null | undefined, digits = 2): string {
  return value == null || Number.isNaN(value) ? "нет данных" : `${value.toLocaleString("ru-RU", { minimumFractionDigits: digits, maximumFractionDigits: digits })} USDT`;
}

export function qty(value: number | null | undefined): string {
  return value == null || Number.isNaN(value) ? "нет данных" : value.toLocaleString("ru-RU", { maximumFractionDigits: 4 });
}

export function pct(value: number | null | undefined): string {
  return value == null || Number.isNaN(value) ? "нет данных" : `${value.toLocaleString("ru-RU", { maximumFractionDigits: 2 })}%`;
}

export function price(value: number | null | undefined): string {
  return value == null || Number.isNaN(value) ? "нет данных" : value.toFixed(4);
}
