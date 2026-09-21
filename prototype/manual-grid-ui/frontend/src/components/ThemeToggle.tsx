import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export type Theme = "dark" | "light";
const THEME_KEY = "manual-grid-theme";

function readTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  return window.localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark";
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => readTheme());
  useEffect(() => { applyTheme(theme); window.localStorage.setItem(THEME_KEY, theme); }, [theme]);
  const next = theme === "dark" ? "light" : "dark";
  return <button type="button" className="theme-toggle" aria-label={`Включить ${next === "light" ? "светлую" : "тёмную"} тему`} title={`Включить ${next === "light" ? "светлую" : "тёмную"} тему`} onClick={() => setTheme(next)}>{theme === "dark" ? <Sun size={16}/> : <Moon size={16}/>}<span>{theme === "dark" ? "Светлая тема" : "Тёмная тема"}</span></button>;
}
